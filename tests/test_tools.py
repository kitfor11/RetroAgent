"""工具单元测试：路径解析（任意路径）+ 字符串工具 + 软删除。

现在按需求放开到「任意路径」：绝对路径直接用，相对路径以默认工作目录为基准。
删除是软删除（移到回收站），可恢复——这是对不可逆操作留的后路，值得测。
"""
from app.agent.tools import (
    SANDBOX_ROOT,
    _resolve_path,
    count_words,
    delete_file,
    reverse_text,
    to_lower,
    to_upper,
)


def test_relative_path_resolves_under_workdir():
    p = _resolve_path("report.pdf")
    assert p == SANDBOX_ROOT / "report.pdf"


def test_absolute_path_anywhere_is_allowed(tmp_path):
    outside = tmp_path / "somefile.txt"
    assert _resolve_path(str(outside)) == outside


def test_parent_traversal_is_now_allowed():
    # 放开后 ".." 不再拦截，会解析到工作目录的父目录
    p = _resolve_path("../up.txt")
    assert p == SANDBOX_ROOT.parent / "up.txt"


def test_delete_moves_to_trash(tmp_path, monkeypatch):
    # 把回收站指到测试临时目录，避免污染真实 .trash
    trash = tmp_path / ".trash"
    monkeypatch.setattr("app.agent.tools.TRASH_DIR", trash)

    f = tmp_path / "del.txt"
    f.write_text("hi", encoding="utf-8")
    msg = delete_file(str(f))

    assert not f.exists()                    # 原位置没了
    assert "trash" in msg
    assert any(p.name.endswith("del.txt") for p in trash.iterdir())  # 进了回收站


def test_string_tools():
    assert count_words("hello world") == 2
    assert reverse_text("abc") == "cba"
    assert to_upper("ab") == "AB"
    assert to_lower("AB") == "ab"
