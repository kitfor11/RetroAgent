"""记忆检索：给定任务，找出所有相关的教训。

和技能检索（skills/retrieve.py）的区别：
- 技能检索：只返回「最相似的一条技能」（复用一个就够了）
- 记忆检索：返回「所有超过阈值的教训」（多个坑都要提醒）
"""
from typing import List

from app.skills.embedding import Embedder, cosine_similarity
from app.skills.models import Memory


def retrieve_memories(
    task: str,
    memories: List[Memory],
    embedder: Embedder,
    threshold: float = 0.3,
) -> List[Memory]:
    """找出和任务相关的所有教训（相似度 ≥ 阈值）。"""
    if not memories:
        return []

    texts = [task] + [m.context for m in memories]
    vecs = embedder.encode(texts)
    task_vec = vecs[0]

    results: List[Memory] = []
    for i, m in enumerate(memories):
        score = cosine_similarity(task_vec, vecs[1 + i])
        if score >= threshold:
            results.append(m)

    return results
