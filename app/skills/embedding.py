"""文本向量化：把文字变成数值向量，用于算相似度。

这是「检索」的基础：计算机不懂文字含义，只懂数字。
embedding 就是把文字「翻译」成向量，让意思相近的文字，向量也相近。

MVP 用「字符 n-gram」：把文字切成重叠的小片段（如 3 个字符一段）。
相比「词袋」（按整个词匹配），它对词形变化更鲁棒——
"reverse" 和 "reverses" 共享大量 3-gram，相似度会高很多。
（生产环境会换成真实 embedding 模型，但「文字→向量→算相似度」的流程完全一样。）
"""
import re

import numpy as np


def char_ngrams(text: str, n: int = 3) -> list[str]:
    """把文本切成字符 n-gram（重叠的 n 字符片段）。

    先去空白和标点（保留字母/数字/汉字等 Unicode 字词字符）、小写化，
    再加首尾边界符 "#"，这样短词和首尾的字符也有完整片段。
    """
    text = re.sub(r"[^\w]", "", text.lower())
    text = "#" + text + "#"
    return [text[i:i + n] for i in range(len(text) - n + 1)]


def build_vocab(texts: list[str]) -> list[str]:
    """收集所有文本的 n-gram，去重排序，作为词表（向量的维度）。"""
    vocab = set()
    for t in texts:
        vocab.update(char_ngrams(t))
    return sorted(vocab)


def text_to_vec(text: str, vocab: list[str]) -> np.ndarray:
    """把文本转成 n-gram 频率向量：每个维度 = 对应片段出现的次数。"""
    grams = char_ngrams(text)
    return np.array([grams.count(g) for g in vocab], dtype=float)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """余弦相似度：两个向量夹角的余弦，越接近 1 越相似，0 = 无关。

    公式：cos = (a·b) / (|a| * |b|)
    """
    dot = np.dot(a, b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return dot / denom
