"""Agent 使用文档 RAG 工具演示：让 Agent 自己调用 search_docs 检索知识库回答。

用法：venv/Scripts/python tests/demo_agent_search.py

流程：铺几个「公司文档」→ 建库 → 给 Agent 一个需要查文档的任务 →
Agent 自己调用 search_docs 工具检索相关片段 → 给出带依据的答案。
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agent.react_loop import run
from app.agent.tools import SANDBOX_ROOT
from app.rag.indexer import index_directory
from app.rag.store import get_store


def setup() -> None:
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT)
    SANDBOX_ROOT.mkdir()
    (SANDBOX_ROOT / "公司介绍.txt").write_text(
        "RetroAgent 是一个会复盘的 AI Agent，2024 年成立于杭州。"
        "核心理念是：完成任务后总结经验，越用越强。",
        encoding="utf-8",
    )
    (SANDBOX_ROOT / "产品手册.md").write_text(
        "RetroAgent 核心功能：技能库（成功经验复用）、经验记忆（失败教训避坑）、"
        "文件整理助手、OCR 看图识字、文档问答检索。",
        encoding="utf-8",
    )


def main() -> None:
    setup()

    # 先把文档建库（search_docs 工具首次调用也会自动建库，这里显式建一次更直观）
    store = get_store()
    store.reset()
    index_directory(SANDBOX_ROOT, store)

    print("=" * 60)
    print("RetroAgent 文档 RAG 工具演示（Agent 自己调用 search_docs）")
    print("=" * 60)

    task = "公司文档里说 RetroAgent 的核心功能有哪些？请检索知识库后回答。"

    print(f"任务：{task}\n")
    print("-" * 60)

    answer, trace = run(task, max_steps=8)

    print("【完整思考链 CoT】")
    for i, step in enumerate(trace, 1):
        print(f"\n──── 第 {i} 步 ────")
        print(step)

    print("\n" + "=" * 60)
    print(f"最终答案：{answer}")
    print("=" * 60)


if __name__ == "__main__":
    main()
