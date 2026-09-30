"""Chroma 向量库封装：存 chunk、按问题检索 top-k。

Chroma 是开源的「嵌入数据库」：把文字 + 向量 + 元数据 add 进去，
query 时按相似度返回 top-k。这里我们用自己的 Embedder 生成向量，
Chroma 只负责「存 + 快查 + 持久化到磁盘」。

注意 import 顺序：必须先 import config（它会设置 protobuf 兼容开关），
再 import chromadb，否则 paddle 的老生成代码会因 protobuf 版本冲突报错。
"""
from app.config import settings
import chromadb

from app.skills.embedding import get_embedder


class ChromaStore:
    """文档 chunk 的向量库。数据持久化到本地目录，重启不丢。"""

    def __init__(self, collection_name: str = "documents"):
        # PersistentClient：本地模式，数据存磁盘（区别于 EphemeralClient 的内存模式）
        self._client = chromadb.PersistentClient(path=settings.chroma_dir)
        # collection 类似一张表；get_or_create 重复初始化不报错
        self._collection = self._client.get_or_create_collection(name=collection_name)
        self._embedder = get_embedder()

    def reset(self) -> None:
        """清空并重建（demo 每次从头索引时用）。"""
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(name=name)

    def add_chunks(self, chunks: list[str], sources: list[str]) -> None:
        """把一批 chunk 向量化后入库，附带来源文件名。"""
        if not chunks:
            return
        embeddings = self._embedder.encode(chunks)  # 形状 (n, dim)
        self._collection.add(
            ids=[f"{src}#{i}" for i, src in enumerate(sources)],
            documents=chunks,
            metadatas=[{"source": src} for src in sources],
            embeddings=embeddings.tolist(),  # Chroma 要 list[list[float]]
        )

    def search(self, question: str, k: int = 3) -> list[dict]:
        """检索与问题最相似的 k 个 chunk，返回 [{text, source}, ...]。"""
        q_vec = self._embedder.encode([question])[0].tolist()
        res = self._collection.query(query_embeddings=[q_vec], n_results=k)
        hits = []
        for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
            hits.append({"text": doc, "source": meta.get("source", "?")})
        return hits
