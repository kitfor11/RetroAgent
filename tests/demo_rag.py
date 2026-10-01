"""文档 RAG 演示：把文件建成向量库，问答时检索相关片段、带来源回答。

用法：venv/Scripts/python tests/demo_rag.py

流程：铺几个文件（含一张 OCR 才能读的图片）→ 索引进 Chroma →
问几个问题 → 展示「检索到的来源 + LLM 回答」。
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw, ImageFont

from app.agent.tools import SANDBOX_ROOT
from app.rag.indexer import index_directory
from app.rag.qa import answer_question
from app.rag.store import ChromaStore

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
]


def _load_font(size: int = 40):
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def setup() -> None:
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT)
    SANDBOX_ROOT.mkdir()

    (SANDBOX_ROOT / "公司介绍.txt").write_text(
        "RetroAgent 是一个会复盘的 AI Agent，由一支小团队于 2024 年在杭州创立。"
        "核心思想是：Agent 完成任务后会总结经验，越用越强。",
        encoding="utf-8",
    )
    (SANDBOX_ROOT / "产品手册.md").write_text(
        "RetroAgent 的核心功能包括：技能库（成功经验复用）、经验记忆（失败教训避坑）、"
        "文件整理助手、OCR 看图识字、文档问答检索。",
        encoding="utf-8",
    )

    # 一张「内容藏在图里」的扫描件：只有 OCR 能读出来
    img = Image.new("RGB", (1100, 150), "white")
    ImageDraw.Draw(img).text(
        (20, 50), "会议纪要：下季度推出多语言支持", fill="black", font=_load_font()
    )
    img.save(SANDBOX_ROOT / "会议纪要.png")


def main() -> None:
    setup()

    print("=" * 60)
    print("RetroAgent 文档 RAG 演示（Chroma 向量库 + 带引用问答）")
    print("=" * 60)

    # 1. 建库：把沙盒所有文件读出来、切片、向量化、入 Chroma
    store = ChromaStore(collection_name="demo_docs")
    store.reset()
    n = index_directory(SANDBOX_ROOT, store)
    print(f"\n已索引 {n} 个 chunk（含 OCR 读出的图片文字）\n")

    # 2. 问答
    questions = [
        "RetroAgent 的核心功能有哪些？",
        "团队在哪个城市？",
        "下季度要推出什么功能？",
    ]
    for q in questions:
        print(f"问：{q}")
        print(f"答：{answer_question(q, store)}\n")

    print("=" * 60)


if __name__ == "__main__":
    main()
