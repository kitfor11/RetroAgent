"""技能数据模型：定义「一条技能」长什么样。

这是整个项目的地基——技能怎么存、怎么检索、怎么复用，全围着这个类转。
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Skill:
    """一条可复用的技能。

    字段按用途分三组：
    - 检索（找「和当前任务像不像」）：description + embedding
    - 判断能否用（检索后过滤）：preconditions
    - 复用（照做）：steps，以及 score / use_count 这类元数据
    """

    name: str                    # 技能名（人看的，如「文本摘要」）
    description: str             # 描述：解决什么问题 —— 检索匹配靠它
    steps: str                   # 具体步骤：怎么做 —— 复用靠它

    preconditions: str = ""      # 适用条件/前提（空字符串表示无限制）
    embedding: List[float] = field(default_factory=list)  # description 的语义向量
    score: float = 0.5           # 置信度/评分：复用效果越好越高（初始中性 0.5）
    use_count: int = 0           # 被复用过的次数
    created_at: float = 0.0      # 创建时间（Unix 时间戳）
    id: str = ""                 # 唯一标识（入库时生成 UUID）


@dataclass
class Memory:
    """一条经验教训：让 Agent 记住「在什么情境下栽过跟头、怎么避开」。

    字段对照 Skill（两者是对称的）：
    - context（情境）↔ Skill.description（描述）：都用于检索匹配
    - lesson（教训）↔ Skill.steps（步骤）：都是核心内容
    """

    context: str                 # 情境：什么情况下会触发这个教训 —— 检索匹配靠它
    lesson: str                  # 教训：栽了什么跟头 + 怎么避坑 —— 避坑靠它

    embedding: List[float] = field(default_factory=list)  # context 的语义向量
    created_at: float = 0.0      # 创建时间（Unix 时间戳）
    id: str = ""                 # 唯一标识（入库时生成 UUID）

