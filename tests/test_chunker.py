"""切片器单元测试：chunk_text 的边界情况。

纯函数、无任何依赖，最适合做单元测试的入门例子。
"""
from app.rag.chunker import chunk_text


def test_empty_text_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_is_single_chunk():
    # 文本长度 ≤ chunk_size 时，整段作为一个 chunk 返回
    assert chunk_text("hello", chunk_size=100) == ["hello"]
    assert chunk_text("hello", chunk_size=5) == ["hello"]  # 正好等于 chunk_size


def test_long_text_splits_with_overlap():
    # 手动推演：10 个字符，chunk_size=6，overlap=2
    # start=0 -> "abcdef"；start = 6-2 = 4 -> "efghij"（"ef" 是重叠部分）
    chunks = chunk_text("abcdefghij", chunk_size=6, overlap=2)
    assert chunks == ["abcdef", "efghij"]


def test_chunks_are_nonempty_and_cover_text():
    # 注意：chunk_text 会先 strip 掉首尾空白，所以这里用无首尾空白的文本
    text = "The quick brown fox jumps over the lazy dog"
    chunks = chunk_text(text, chunk_size=30, overlap=10)
    assert all(c for c in chunks)          # 没有空 chunk
    assert chunks[0].startswith(text[:5])  # 首块从原文开头开始
    assert chunks[-1].endswith(text[-5:])  # 末块在原文结尾结束（没漏字）
