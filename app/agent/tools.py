"""工具集：Agent 能调用的「手」。

每个工具 = 一个普通 Python 函数 + 一段描述（docstring）。
描述很重要：模型就是靠读这段描述，判断「现在该用哪个工具、怎么传参」。

TOOLS 是注册表：名字 -> 函数。Agent 说「我要调 count_words」，
我们就从这张表里按名字查到函数来执行。

安全设计：所有文件工具都被限制在「沙盒目录」（SANDBOX_ROOT）内，
不能读写沙盒外的真实文件。这是对不可逆操作（移动/删除）的第一道安全网。
"""
import shutil
from pathlib import Path
from typing import Any, Callable, Dict

from app.config import settings

TOOLS: Dict[str, Callable] = {}

# 沙盒根目录：文件工具只能碰这个目录（绝对路径）。默认 demo_files，可在 .env 里改。
SANDBOX_ROOT = Path(settings.sandbox_root).resolve()


def _ensure_in_sandbox(path: str) -> Path:
    """把路径解析成绝对路径，并确保它在沙盒内，否则抛错。

    这是安全网：Agent 是 LLM 驱动的，可能「想歪」，不能让它乱读写
    沙盒外的真实文件。破坏沙盒 -> ValueError -> 被 ReAct 循环当成
    一次失败（还能记成教训）。

    注意：相对路径（如 "report.pdf"）会先拼到沙盒根目录下再解析，
    因为 list_files 只回传文件名，Agent 自然会拿文件名去操作。
    只有用 `..` 越界（如 "../secret.txt"）才会被拦下。
    """
    p = Path(path)
    if not p.is_absolute():
        p = SANDBOX_ROOT / p  # 相对路径默认相对于沙盒根目录
    p = p.resolve()
    if not p.is_relative_to(SANDBOX_ROOT):
        raise ValueError(f"Path outside sandbox: {path}")
    return p


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


@register
def list_files(path: str) -> str:
    """List all files directly inside a directory (one per line: name, size in KB).
    Input: path - the directory to inspect. Output: a text list of files."""
    dir_path = _ensure_in_sandbox(path)
    if not dir_path.exists():
        return f"Directory not found: {path}"
    lines = []
    for p in sorted(dir_path.iterdir()):  # iterdir 遍历目录下的每一项
        if p.is_file():                   # 只挑「文件」，跳过子目录
            size_kb = p.stat().st_size / 1024
            lines.append(f"{p.name}  ({size_kb:.1f} KB)")
    if not lines:
        return f"(empty directory: {path})"
    return "\n".join(lines)


@register
def read_text(path: str) -> str:
    """Read a text file and return its content (truncated to 2000 chars).
    Input: path - the file to read. Output: the file's text content."""
    p = _ensure_in_sandbox(path)
    if not p.exists():
        return f"File not found: {path}"
    # errors="ignore"：遇到非 UTF-8 的字节就跳过，不崩；[:2000] 防止超长文件撑爆 prompt
    return p.read_text(encoding="utf-8", errors="ignore")[:2000]


@register
def make_dir(path: str) -> str:
    """Create a directory (and any missing parents).
    Input: path - the directory to create. Output: a confirmation message."""
    p = _ensure_in_sandbox(path)
    p.mkdir(parents=True, exist_ok=True)  # parents=True 递归建目录；exist_ok=True 已存在不报错
    return f"Created directory: {path}"


@register
def move_file(src: str, dst: str) -> str:
    """Move or rename a file from src to dst.
    Input: src - current path, dst - target path. Output: a confirmation message."""
    src_p = _ensure_in_sandbox(src)
    dst_p = _ensure_in_sandbox(dst)
    if not src_p.exists():
        return f"File not found: {src}"
    dst_p.parent.mkdir(parents=True, exist_ok=True)  # 先保证目标目录存在
    shutil.move(str(src_p), str(dst_p))
    return f"Moved {src} -> {dst}"


def call_tool(name: str, args: Dict[str, Any]) -> Any:
    """按名字执行工具。找不到工具时报错（这样 Agent 乱编工具名时能被发现）。"""
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name](**args)
