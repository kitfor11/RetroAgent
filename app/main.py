"""FastAPI 入口：把 EvoAgent 包装成 RESTful API。

这是「接口层」——只负责对外暴露接口，业务逻辑都在 agent/ 里。
"""
from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.agent import solve_task
from app.agent.tools import SANDBOX_ROOT
from app.memory.store import RedisMemoryStore
from app.rag.indexer import index_directory
from app.rag.qa import rag_answer
from app.rag.store import get_store
from app.skills.store import RedisSkillStore

app = FastAPI(title="EvoAgent")

# 全局存储实例：接口共享同一份技能库和记忆库
# 从 JSON 文件换成 Redis——只改了这两行，业务逻辑零改动
skill_store = RedisSkillStore()
memory_store = RedisMemoryStore()


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
