"""索引器：把目录下的文件变成可检索的向量（RAG 的「建库」阶段）。

对每个文件：读内容（文本直接读，图片走 OCR）→ 切片 → 向量化 → 入 Chroma。

索引不是「所有文件都读」：只挑值得检索的（文本/文档类型），
跳过虚拟环境、依赖、缓存等目录——否则选个大目录（如项目根）会遍历
几万个文件，把接口卡死。
"""
import os
from pathlib import Path

from app.rag.chunker import chunk_text
from app.rag.store import ChromaStore

# 可索引的文本类型（白名单）：只读这些，跳过二进制/压缩包等
_TEXT_SUFFIXES = {
    ".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".log",
    ".html", ".htm", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".toml",
    ".py", ".js", ".ts", ".java", ".sh", ".css", ".sql", ".go", ".rs",
}
# 需要走 OCR 的图片扩展名
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}

# 索引时跳过的目录（虚拟环境/依赖/缓存/回收站等，文件极多且没有检索价值）
_SKIP_DIRS = {
    "venv", ".venv", "env", ".git", ".hg", ".svn", "__pycache__",
    "node_modules", "site-packages", "dist", "build", ".trash",
    "chroma_db", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    ".claude",
}

# 单文件超过这个大小（字节）就不索引，避免超大文件拖慢整个索引
_MAX_FILE_SIZE = 1_000_000  # 1MB


def _read_file(p: Path) -> str:
    """读文件内容：图片走 OCR，其余按文本读。

    索引是「尽力而为」：任何单个文件失败（读不了、OCR 抛错、损坏图片等）
    都返回空串跳过，绝不让一个坏文件把整次索引搞崩（否则 /index 会 500）。
    """
    try:
        if p.suffix.lower() in _IMAGE_SUFFIXES:
            from app.multimodal.ocr import get_ocr  # 懒加载，只有碰到图片才加载 OCR
            return get_ocr().read_text(str(p))
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""  # 单个文件读不了就跳过，别让整次索引崩掉


def _should_index(p: Path) -> bool:
    """判断文件是否值得索引：类型可读 + 大小合理。"""
    suffix = p.suffix.lower()
    if suffix not in _TEXT_SUFFIXES and suffix not in _IMAGE_SUFFIXES:
        return False
    try:
        return p.stat().st_size <= _MAX_FILE_SIZE
    except OSError:
        return False


def index_directory(directory: Path, store: ChromaStore) -> int:
    """把目录下的可读文件索引进向量库，返回入库的 chunk 总数。"""
    chunks: list[str] = []
    sources: list[str] = []
    for root, dirs, files in os.walk(directory):
        # 剪枝：跳过 venv/.git 等目录，不往下遍历（否则选项目根会遍历几万文件）
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            p = Path(root) / name
            if not _should_index(p):
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
