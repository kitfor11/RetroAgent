"""索引器：把目录下的文件变成可检索的向量（RAG 的「建库」阶段）。

对每个文件：读内容（文本直接读，图片走 OCR）→ 切片 → 向量化 → 入 Chroma。
"""
from pathlib import Path

from app.rag.chunker import chunk_text
from app.rag.store import ChromaStore

# 需要走 OCR 的图片扩展名
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


def _read_file(p: Path) -> str:
    """读文件内容：图片走 OCR，其余按文本读。"""
    if p.suffix.lower() in _IMAGE_SUFFIXES:
        from app.multimodal.ocr import get_ocr  # 懒加载，只有碰到图片才加载 OCR
        return get_ocr().read_text(str(p))
    return p.read_text(encoding="utf-8", errors="ignore")


def index_directory(directory: Path, store: ChromaStore) -> int:
    """把目录下所有文件索引进向量库，返回入库的 chunk 总数。"""
    chunks: list[str] = []
    sources: list[str] = []
    for p in sorted(directory.rglob("*")):
        if not p.is_file():
            continue
        text = _read_file(p)
        if not text.strip():
            continue
        rel = str(p.relative_to(directory))  # 来源用相对路径，展示更清晰
        for chunk in chunk_text(text):
            chunks.append(chunk)
            sources.append(rel)
    store.add_chunks(chunks, sources)
    return len(chunks)
