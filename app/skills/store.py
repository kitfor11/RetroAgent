"""技能存储：把技能存进仓库。

设计要点：接口 + 可替换实现。
- SkillStore 是「接口」，约定好有哪些方法（save / list_all）。
- JsonSkillStore 是 MVP 实现（存 JSON 文件）。
- RedisSkillStore 是用 Redis 的实现（换它只需改 main.py 一行，别处零改动）。
"""
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List

import redis

from app.skills.models import Skill


class SkillStore:
    """技能存储的接口：先约定方法，具体怎么存由子类实现。"""

    def save(self, skill: Skill) -> Skill:
        raise NotImplementedError

    def update(self, skill: Skill) -> Skill:
        raise NotImplementedError

    def list_all(self) -> List[Skill]:
        raise NotImplementedError


class JsonSkillStore(SkillStore):
    """MVP 实现：把技能存进一个 JSON 文件。"""

    def __init__(self, path: str = "skills.json") -> None:
        self.path = Path(path)

    def _load(self) -> List[dict]:
        """从文件读出所有技能（dict 列表）。文件不存在则返回空列表。"""
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _dump(self, skills: List[dict]) -> None:
        """把所有技能写回文件。ensure_ascii=False 让中文能正常显示。"""
        self.path.write_text(
            json.dumps(skills, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save(self, skill: Skill) -> Skill:
        """保存一条技能：先补全 id 和创建时间，再追加进文件。"""
        if not skill.id:
            skill.id = uuid.uuid4().hex
        if not skill.created_at:
            skill.created_at = time.time()

        skills = self._load()
        skills.append(asdict(skill))
        self._dump(skills)
        return skill

    def list_all(self) -> List[Skill]:
        """读出所有技能，重建成 Skill 对象列表。"""
        return [Skill(**data) for data in self._load()]

    def update(self, skill: Skill) -> Skill:
        """按 id 找到并覆盖一条技能（比如 use_count +1 后写回）。"""
        skills = self._load()
        for i, data in enumerate(skills):
            if data["id"] == skill.id:
                skills[i] = asdict(skill)
                break
        self._dump(skills)
        return skill


class RedisSkillStore(SkillStore):
    """用 Redis 的 hash 存技能：field 是技能名，value 是序列化后的 JSON。

    为什么从 list 换成 hash？
    - list 只能 rpush 追加，没法按名字「覆盖/更新」→ 导致重复技能、use_count 存不回去。
    - hash 的 hset 用同一个 field 写入时会覆盖旧值 → 天然查重；
      更新（use_count +1 后写回）也就是再 hset 一次。
    选对数据结构，是使用 Redis 的核心能力。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        url: str = "",
        key: str = "retroagent:skills",
    ) -> None:
        # decode_responses=True：让 Redis 返回字符串而不是字节，省去手动 decode
        if url:
            # 托管 Redis 用连接串（含密码/SSL），本地开发用 host+port
            self.r = redis.Redis.from_url(url, decode_responses=True)
        else:
            self.r = redis.Redis(host=host, port=port, decode_responses=True)
        self.key = key  # 带命名空间的 key，是 Redis 的最佳实践

    def save(self, skill: Skill) -> Skill:
        """保存：补全元数据后 hset 写入（同名 field 自动覆盖 → 天然查重）。"""
        if not skill.id:
            skill.id = uuid.uuid4().hex
        if not skill.created_at:
            skill.created_at = time.time()

        self.r.hset(self.key, skill.name, json.dumps(asdict(skill), ensure_ascii=False))
        return skill

    def update(self, skill: Skill) -> Skill:
        """更新：hset 用同名 field 覆盖，把改动（如 use_count）写回。"""
        self.r.hset(self.key, skill.name, json.dumps(asdict(skill), ensure_ascii=False))
        return skill

    def list_all(self) -> List[Skill]:
        """读取：hgetall 取出整个 hash，每个 value 反序列化成 Skill。"""
        raw = self.r.hgetall(self.key)  # 返回 {name: json}
        return [Skill(**json.loads(v)) for v in raw.values()]
