"""文本向量化：把文字变成数值向量，用于算相似度。

这是「检索」的基础：计算机不懂文字含义，只懂数字。
embedding 就是把文字「翻译」成向量，让意思相近的文字，向量也相近。

这里用「接口 + 可替换实现」：
- CharNgramEmbedder：字符 n-gram（零依赖，只比字面、不比语义）
- SentenceTransformerEmbedder：真实语义模型（多语言，比「意思」）

业务代码只依赖 Embedder 接口，通过 get_embedder() 按配置选择具体实现。
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

class Embedder:
    """向量化接口：把一批文本变成一批向量（形状 n×维度）。"""
    def encode(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class CharNgramEmbedder(Embedder):
    """字符 n-gram 实现：把现在的函数包进来，行为不变。"""
    def encode(self, texts: list[str]) -> np.ndarray:
        vocab = build_vocab(texts)
        return np.array([text_to_vec(t, vocab) for t in texts])



class SentenceTransformerEmbedder(Embedder):
    """真实语义模型实现。"""
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts)


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """按配置返回全局唯一的 embedder（惰性创建，只建一次）。

    为什么惰性：真实模型首次要下载并载入（慢、占内存），
    所以不在一 import 时就建，而是第一次真正用到检索时才建。
    """
    global _embedder
    if _embedder is None:
        from app.config import settings

        if settings.embedding_backend == "sentence_transformers":
            _embedder = SentenceTransformerEmbedder(settings.embedding_model)
        else:
            _embedder = CharNgramEmbedder()
    return _embedder
 
