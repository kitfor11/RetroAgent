"""Agent 的完整进化执行：检索 → 复用/解决 → 反思入库。

这是整个项目的「灵魂」串起来的入口：
接到任务，先翻技能库，有就复用；没有就自己解决。
- 解决成功 → 提炼成技能（复用）
- 解决失败 → 提炼成教训（避坑），并注入下次的 prompt
"""
from typing import Dict

from app.agent.react_loop import run
from app.agent.reflect import judge_success, reflect, reflect_failure
from app.memory.retrieve import retrieve_memories
from app.skills.retrieve import retrieve
from app.skills.store import SkillStore


def solve_task(task: str, skill_store: SkillStore, memory_store) -> Dict:
    """执行完整进化链路，返回一个结果字典。

    结果里 method 字段告诉调用方这次是：
    - reused_skill：复用已有技能
    - solved：自己解决成功，并学成新技能
    - failed：解决失败，并记成教训

    memory_store 只要是「有 save / list_all 方法的存储」就行（和技能库同一套接口约定）。
    """
    # 1. 检索相关教训，等会儿注入 prompt 让 agent 避坑
    lessons = retrieve_memories(task, memory_store.list_all())

    # 2. 检索技能库：有没有和任务相似的技能
    existing = retrieve(task, skill_store.list_all())
    if existing:
        existing.use_count += 1  # 复用次数 +1
        skill_store.update(existing)  # 写回 Redis，持久化复用次数
        return {
            "answer": existing.steps,
            "method": "reused_skill",
            "skill": existing.name,
        }

    # 3. 未命中：ReAct 自己解决（把历史教训喂进去）
    answer, trace = run(task, lessons=lessons)

    # 4. 分叉：先用模型判断「是否真的成功」，再决定提炼成技能还是教训
    #    （机械信号 answer is None + 模型裁判 judge_success 双保险）
    if answer is None or not judge_success(task, answer, trace):
        lesson = reflect_failure(task, trace)
        memory_store.save(lesson)
        return {
            "answer": answer,
            "method": "failed",
            "learned_lesson": lesson.lesson,
        }

    new_skill = reflect(task, trace)
    skill_store.save(new_skill)
    return {
        "answer": answer,
        "method": "solved",
        "learned_skill": new_skill.name,
    }
