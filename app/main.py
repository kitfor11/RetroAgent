"""FastAPI 入口：把 EvoAgent 包装成 RESTful API。

这是「接口层」——只负责对外暴露接口，业务逻辑都在 agent/ 里。
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent.agent import solve_task
from app.agent.tools import SANDBOX_ROOT
from app.config import settings
from app.memory.store import RedisMemoryStore
from app.rag.indexer import index_directory
from app.rag.qa import rag_answer
from app.rag.store import get_store
from app.skills.store import RedisSkillStore

app = FastAPI(title="EvoAgent")

# 全局存储实例：接口共享同一份技能库和记忆库
# 从 JSON 文件换成 Redis——只改了这两行，业务逻辑零改动
# 托管部署配 REDIS_URL（连接串），本地开发用 REDIS_HOST/PORT
skill_store = RedisSkillStore(
    host=settings.redis_host, port=settings.redis_port, url=settings.redis_url
)
memory_store = RedisMemoryStore(
    host=settings.redis_host, port=settings.redis_port, url=settings.redis_url
)


@app.get("/health")
def health():
    """健康检查：部署平台用它探活，返回 ok 就代表服务起来了。"""
    return {"status": "ok"}


class SolveRequest(BaseModel):
    """提交任务的请求体：只需要一个 task 字段。"""

    task: str


@app.post("/solve")
def solve(req: SolveRequest):
    """提交任务，走完整进化链路（检索 → 复用/解决 → 反思入库）。"""
    return solve_task(req.task, skill_store, memory_store)


@app.get("/skills")
def list_skills():
    """查看技能库（只列出技能名，避免返回太臃肿）。"""
    return {"skills": [s.name for s in skill_store.list_all()]}


@app.get("/memories")
def list_memories():
    """查看长期记忆（只列出教训内容）。"""
    return {"memories": [m.lesson for m in memory_store.list_all()]}


class AskRequest(BaseModel):
    """文档问答请求：问题 + 可选检索条数。"""

    question: str
    k: int = 3


@app.post("/index")
def index_docs():
    """把沙盒目录下的文件索引进向量库（先清空再全量索引），返回入库 chunk 数。"""
    store = get_store()
    store.reset()
    n = index_directory(SANDBOX_ROOT, store)
    return {"indexed_chunks": n}


@app.post("/ask")
def ask(req: AskRequest):
    """文档问答：检索沙盒文件内容，带引用来源回答。"""
    return rag_answer(req.question, get_store(), k=req.k)


def _build_tree(path: Path) -> dict:
    """递归把沙盒目录变成 {name, type, children} 树，供前端「文件面板」渲染。"""
    if not path.exists():
        return {"name": path.name, "type": "dir", "children": []}
    children = []
    for p in sorted(path.iterdir()):
        if p.is_dir():
            children.append(_build_tree(p))
        else:
            children.append({
                "name": p.name,
                "type": "file",
                "size_kb": round(p.stat().st_size / 1024, 1),
            })
    return {"name": path.name, "type": "dir", "children": children}


@app.get("/files")
def list_sandbox_files():
    """列出沙盒目录的文件树（只读，给前端文件面板展示）。"""
    return _build_tree(SANDBOX_ROOT)


# 前端静态文件目录（index.html / style.css / app.js）
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# 挂载静态目录：html=True 让根路径 "/" 直接返回 index.html
# 必须放在所有 API 路由之后，否则会吞掉 /solve、/ask 等接口
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
