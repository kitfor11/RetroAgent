"""检索单元测试：技能检索（返回最像的一条）+ 记忆检索（返回所有相关教训）。

都用字符 n-gram 嵌入器（零依赖、纯本地），所以测试不联网、不加载模型。
"""
from app.memory.retrieve import retrieve_memories
from app.skills.embedding import CharNgramEmbedder
from app.skills.models import Memory, Skill
from app.skills.retrieve import retrieve


def _skill(name, description):
    return Skill(name=name, description=description, steps="do it")


def test_retrieve_empty_skills_returns_none():
    assert retrieve("reverse text", [], CharNgramEmbedder()) is None


def test_retrieve_finds_the_matching_skill():
    skills = [
        _skill("reverse-text", "reverse the characters of a string"),
        _skill("make-coffee", "brew a cup of coffee"),
    ]
    got = retrieve("reverse the string please", skills, CharNgramEmbedder())
    assert got is not None
    assert got.name == "reverse-text"  # 命中的是「反转」技能，不是「冲咖啡」


def test_retrieve_below_threshold_returns_none():
    # 阈值拉高到 0.9，完全无关的技能不可能达标 -> 返回 None（表示「没有可复用技能」）
    skills = [_skill("make-coffee", "brew a cup of coffee")]
    got = retrieve("reverse a string", skills, CharNgramEmbedder(), threshold=0.9)
    assert got is None


def test_retrieve_memories_empty_returns_empty():
    assert retrieve_memories("x", [], CharNgramEmbedder()) == []


def test_retrieve_memories_returns_all_relevant():
    memories = [
        Memory(context="reverse text", lesson="loop method"),
        Memory(context="make coffee", lesson="coffee method"),
        Memory(context="reverse string", lesson="slicing method"),
    ]
    got = retrieve_memories("reverse the string", memories, CharNgramEmbedder())
    lessons = sorted({m.lesson for m in got})
    # 两条与「反转」相关的都命中，冲咖啡那条被过滤掉
    assert lessons == ["loop method", "slicing method"]
