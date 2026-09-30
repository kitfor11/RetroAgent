"""配置模块：统一读取 .env 里的配置，全项目从这里拿配置。"""
import os

# 【关键】protobuf 兼容开关：paddle 2.6 的生成代码是 protoc 3.x 产的，
# 而 chromadb 需要 protobuf 7.x，两者对 protobuf 版本要求没有交集。
# 设成纯 Python 实现，能兼容老生成代码，让 OCR 和 Chroma 在同一环境共存。
# 必须在任何 protobuf 导入之前设置，所以放最上面。
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from dotenv import load_dotenv

# 把 .env 文件里的 KEY=VALUE 读进程序的环境变量（之后才能用 os.getenv 取到）
load_dotenv()


class Settings:
    """集中管理所有配置项，避免配置散落在各处。

    每个配置项都「先从环境变量取，取不到就用默认值」，
    这样 .env 没配时程序也能跑（只是 key 为空）。
    """

    def __init__(self) -> None:
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.getenv(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        # embedding 后端：ngram（默认，零依赖）或 sentence_transformers（真实语义，需装依赖）
        self.embedding_backend = os.getenv("EMBEDDING_BACKEND", "ngram")
        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        # 文件工具的沙盒目录：只允许读写这个目录（安全网），可在 .env 里改
        self.sandbox_root = os.getenv("SANDBOX_ROOT", "demo_files")
        # OCR 后端：paddle（PaddleOCR，需装 paddleocr/paddlepaddle）或 dummy（不识别，返回提示）
        self.ocr_backend = os.getenv("OCR_BACKEND", "paddle")
        # Chroma 向量库的持久化目录（文档 RAG 用），可在 .env 里改
        self.chroma_dir = os.getenv("CHROMA_DIR", "chroma_db")


# 全局单例：别处 `from app.config import settings` 就能拿到同一份配置
settings = Settings()
