"""记忆检索：给定任务，找出所有相关的教训。

和技能检索（skills/retrieve.py）的区别：
- 技能检索：只返回「最相似的一条技能」（复用一个就够了）
- 记忆检索：返回「所有超过阈值的教训」（多个坑都要提醒）
"""
from typing import List

from app.skills.embedding import build_vocab, cosine_similarity, text_to_vec
from app.skills.models import Memory


def retrieve_memories(
    task: str,
    memories: List[Memory],
    threshold: float = 0.3,
) -> List[Memory]:
    """找出和任务相关的所有教训（相似度 ≥ 阈值）。"""
    if not memories:
        return []

    vocab = build_vocab([m.context for m in memories] + [task])
    task_vec = text_to_vec(task, vocab)

    results: List[Memory] = []
    for m in memories:
        m_vec = text_to_vec(m.context, vocab)
        score = cosine_similarity(task_vec, m_vec)
        if score >= threshold:
            results.append(m)

    return results
