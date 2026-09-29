"""工具集：Agent 能调用的「手」。

每个工具 = 一个普通 Python 函数 + 一段描述（docstring）。
描述很重要：模型就是靠读这段描述，判断「现在该用哪个工具、怎么传参」。

TOOLS 是注册表：名字 -> 函数。Agent 说「我要调 count_words」，
我们就从这张表里按名字查到函数来执行。
"""
from typing import Any, Callable, Dict

TOOLS: Dict[str, Callable] = {}


def register(func: Callable) -> Callable:
    """装饰器：把函数按名字自动登记进 TOOLS 表。"""
    TOOLS[func.__name__] = func
    return func


@register
def count_words(text: str) -> int:
    """Count how many words are in the text. Input: the text. Output: an integer count."""
    return len(text.split())


@register
def reverse_text(text: str) -> str:
    """Reverse the characters of the text. Input: the text. Output: the reversed text."""
    return text[::-1]


@register
def to_upper(text: str) -> str:
    """Convert the text to UPPERCASE. Input: the text. Output: the uppercase text."""
    return text.upper()


@register
def to_lower(text: str) -> str:
    """Convert the text to lowercase. Input: the text. Output: the lowercase text."""
    return text.lower()


def call_tool(name: str, args: Dict[str, Any]) -> Any:
    """按名字执行工具。找不到工具时报错（这样 Agent 乱编工具名时能被发现）。"""
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name](**args)
