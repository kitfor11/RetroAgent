"""工具单元测试：重点测「沙盒安全网」+ 几个字符串工具。

安全是文件工具的第一道防线：Agent 是 LLM 驱动的，可能「想歪」，
所以 _ensure_in_sandbox 必须拦住任何越界路径——这正是最值得测的部分。
"""
import pytest

from app.agent.tools import (
    SANDBOX_ROOT,
    _ensure_in_sandbox,
    count_words,
    reverse_text,
    to_lower,
    to_upper,
)


def test_relative_path_resolves_under_sandbox():
    p = _ensure_in_sandbox("report.pdf")
    assert p == SANDBOX_ROOT / "report.pdf"
    assert p.is_relative_to(SANDBOX_ROOT)


def test_parent_traversal_is_blocked():
    # ".." 越界必须被拦下
    with pytest.raises(ValueError):
        _ensure_in_sandbox("../secret.txt")


def test_absolute_path_outside_is_blocked(tmp_path):
    # tmp_path 是 pytest 的临时目录，肯定在沙盒外
    outside = tmp_path / "secret.txt"
    with pytest.raises(ValueError):
        _ensure_in_sandbox(str(outside))


def test_absolute_path_inside_is_allowed():
    inside = SANDBOX_ROOT / "ok.txt"
    assert _ensure_in_sandbox(str(inside)) == inside


def test_string_tools():
    assert count_words("hello world") == 2
    assert reverse_text("abc") == "cba"
    assert to_upper("ab") == "AB"
    assert to_lower("AB") == "ab"
