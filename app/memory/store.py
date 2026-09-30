"""记忆存储：把教训存进仓库。结构和技能存储（skills/store.py）对称。"""
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List

import redis

from app.skills.models import Memory


class JsonMemoryStore:
    """MVP 实现：把教训存进一个 JSON 文件。"""

    def __init__(self, path: str = "memories.json") -> None:
        self.path = Path(path)

    def _load(self) -> List[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _dump(self, memories: List[dict]) -> None:
        self.path.write_text(
            json.dumps(memories, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save(self, memory: Memory) -> Memory:
        """保存一条教训：先补全 id 和创建时间，再追加进文件。"""
        if not memory.id:
            memory.id = uuid.uuid4().hex
        if not memory.created_at:
            memory.created_at = time.time()

        memories = self._load()
        memories.append(asdict(memory))
        self._dump(memories)
        return memory

    def list_all(self) -> List[Memory]:
        """读出所有教训，重建成 Memory 对象列表。"""
        return [Memory(**data) for data in self._load()]


class RedisMemoryStore:
    """用 Redis 的 list 存教训：和 RedisSkillStore 完全对称。"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        url: str = "",
        key: str = "evoagent:memories",
    ) -> None:
        if url:
            # 托管 Redis 用连接串（含密码/SSL），本地开发用 host+port
            self.r = redis.Redis.from_url(url, decode_responses=True)
        else:
            self.r = redis.Redis(host=host, port=port, decode_responses=True)
        self.key = key

    def save(self, memory: Memory) -> Memory:
        """保存：补全元数据后，序列化并 rpush 到 list 尾部。"""
        if not memory.id:
            memory.id = uuid.uuid4().hex
        if not memory.created_at:
            memory.created_at = time.time()

        self.r.rpush(self.key, json.dumps(asdict(memory), ensure_ascii=False))
        return memory

    def list_all(self) -> List[Memory]:
        """读取：lrange 取出整个 list，每个元素反序列化成 Memory。"""
        raw = self.r.lrange(self.key, 0, -1)
        return [Memory(**json.loads(x)) for x in raw]
