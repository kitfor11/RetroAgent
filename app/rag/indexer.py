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


# 记录当前向量库索引的是哪个目录；工作目录切换后据此判断要不要重建
_indexed_dir: str | None = None


def _get_workdir() -> Path:
    """当前工作目录（懒 import，避免与 tools 的懒 import 形成顶层循环依赖）。"""
    from app.agent.tools import get_workdir
    return get_workdir()


def reindex(store: ChromaStore) -> int:
    """强制重建：清空向量库，全量索引当前工作目录，返回入库 chunk 数。"""
    global _indexed_dir
    store.reset()
    n = index_directory(_get_workdir(), store)
    _indexed_dir = str(_get_workdir())
    return n


def ensure_indexed(store: ChromaStore) -> int:
    """确保向量库索引的是当前工作目录；空库或目录变了就重建，返回 chunk 数。"""
    if store.count() == 0 or _indexed_dir != str(_get_workdir()):
        return reindex(store)
    return store.count()
