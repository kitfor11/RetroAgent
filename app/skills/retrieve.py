"""技能检索：给定任务，从技能库里找最相似的技能（RAG 的「R」）。

流程：任务向量化 → 每个技能（name + description）向量化 → 算余弦相似度 → 找最像的。
再用「阈值」判断：相似度够高（≥ 阈值）才返回技能，否则返回 None，
表示「没有可复用的技能，自己解决」。

为什么同时比 name 和 description：
- name 是浓缩的操作关键词（如 reverse-text），和任务的意图更接近；
- description 是更完整的描述，作为补充。
取两者相似度的较大值，检索更鲁棒。
"""
from typing import List, Optional

from app.skills.embedding import Embedder, cosine_similarity
from app.skills.models import Skill


def retrieve(task: str, skills: List[Skill], embedder: Embedder, threshold: float = 0.3) -> Optional[Skill]:
    """从技能库里找和任务最相似的技能。

    返回：最相似且相似度 ≥ 阈值的技能；没有则返回 None。
    """
    if not skills:
        return None

    # 一次性编码「任务 + 所有技能的 name + description」，向量顺序和 texts 一一对应
    texts = [task]
    for s in skills:
        texts.append(s.name)
        texts.append(s.description)
    vecs = embedder.encode(texts)
    task_vec = vecs[0]  # 第 0 个是任务

    best_skill = None
    best_score = -1.0
    for i, skill in enumerate(skills):
        name_vec = vecs[1 + 2 * i]  # 每个技能占两位：name 在奇数位
        desc_vec = vecs[2 + 2 * i]  # description 在偶数位
        # 同时比 name 和 description，取较大值
        score = max(
            cosine_similarity(task_vec, name_vec),
            cosine_similarity(task_vec, desc_vec),
        )
        if score > best_score:
            best_score = score
            best_skill = skill

    if best_skill is not None and best_score >= threshold:
        return best_skill
    return None
