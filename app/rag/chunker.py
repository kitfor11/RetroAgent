"""切片器：把长文档切成小块（chunk），这是文档 RAG 的第一步。

为什么要切片：
1. 检索粒度——整篇文档太长，向量化后语义被稀释，切成小块才能精准命中；
2. LLM 上下文有限，一次只能塞进几个相关 chunk，而不是整篇文档。

overlap（重叠）让相邻 chunk 有一段重复，防止一句话被切在中间、语义断裂。
"""


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """把文本按固定长度切成 chunk，带 overlap。"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap  # 回退 overlap，和上一块有重叠
    return chunks
