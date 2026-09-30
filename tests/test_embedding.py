"""向量化单元测试：字符 n-gram + 余弦相似度 + n-gram 嵌入器。

这些是检索的地基——先把「文字变向量」这一步测扎实。
"""
import numpy as np
import pytest

from app.skills.embedding import (
    CharNgramEmbedder,
    build_vocab,
    char_ngrams,
    cosine_similarity,
    text_to_vec,
)


def test_char_ngrams_normalizes_and_adds_boundaries():
    # "Hello!" -> 去标点、小写 -> "hello" -> 加边界 "#hello#"
    # 3-gram 逐个滑窗：["#he", "hel", "ell", "llo", "lo#"]
    assert char_ngrams("Hello!", n=3) == ["#he", "hel", "ell", "llo", "lo#"]


def test_char_ngrams_chinese():
    # 中文也是「字」级切分；n=2 时 "你好" -> "#你好#" -> ["#你", "你好", "好#"]
    assert char_ngrams("你好", n=2) == ["#你", "你好", "好#"]


def test_build_vocab_is_sorted_and_deduped():
    vocab = build_vocab(["a", "a", "b"])
    assert vocab == sorted(vocab)          # 有序
    assert len(vocab) == len(set(vocab))   # 无重复


def test_text_to_vec_counts_frequencies():
    # "aa" 的 3-gram 是 ["#aa", "aa#"]，各出现 1 次
    v = text_to_vec("aa", ["#aa", "aa#"])
    assert v.tolist() == [1.0, 1.0]


def test_cosine_identical_is_one():
    a = np.array([1.0, 2.0, 3.0])
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero():
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.0)


def test_cosine_zero_vector_is_zero():
    # 零向量没有方向，相似度定义为 0（避免除零）
    assert cosine_similarity(np.array([0.0, 0.0]), np.array([1.0, 1.0])) == 0.0


def test_embedder_similar_texts_are_closer():
    emb = CharNgramEmbedder()
    vecs = emb.encode(["reverse text", "reverse the text", "make coffee"])
    sim_close = cosine_similarity(vecs[0], vecs[1])
    sim_far = cosine_similarity(vecs[0], vecs[2])
    assert sim_close > sim_far  # 意思近的向量距离更近


def test_embedder_output_shape():
    emb = CharNgramEmbedder()
    vecs = emb.encode(["a", "b", "c"])
    assert vecs.shape[0] == 3   # 一行一条文本
    assert vecs.shape[1] > 0    # 列数 = 词表大小
