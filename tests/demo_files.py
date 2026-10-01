"""文件整理助手演示：真实文件工具 + 可见的 CoT（思维链）。

用法：venv/Scripts/python tests/demo_files.py

这是 RetroAgent 的第一个「落地场景」：把沙盒目录里乱放的文件，按扩展名
整理进分类子目录。会打印 Agent 的完整 ReAct 轨迹，你能直接看到它每步的
「Thought:」——这就是 CoT，推理过程明明白白，不是黑盒。

（技能的「检索→增强→生成」RAG 和「越用越强」的复盘闭环，见 demo_full.py）
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows 控制台默认 GBK，中文会乱码/报错；统一切成 UTF-8（VS Code 终端就是 UTF-8）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agent.react_loop import run
from app.agent.tools import SANDBOX_ROOT


def setup_sample_files() -> None:
    """清空沙盒再铺几个「乱放」的示例文件，保证演示可重复。"""
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT)
    SANDBOX_ROOT.mkdir()
    samples = {
        "report.pdf": "Q3 sales report ...",
        "photo.jpg": "some image bytes ...",
        "notes.txt": "meeting notes ...",
    }
    for name, content in samples.items():
        (SANDBOX_ROOT / name).write_text(content, encoding="utf-8")


def main() -> None:
    setup_sample_files()

    print("=" * 60)
    print("RetroAgent 文件整理助手演示（真实文件工具 + CoT）")
    print("=" * 60)
    print(f"沙盒目录：{SANDBOX_ROOT}\n")

    task = (
        f"帮我整理目录 {SANDBOX_ROOT}：把里面的文件按扩展名分类，"
        "相同类型的放进同一个子目录（pdf 归 pdf/，图片归 images/，文本归 text/）。"
    )

    print(f"任务：{task}\n")
    print("-" * 60)

    answer, trace = run(task, max_steps=12)

    print("【完整思考链 CoT —— 每一步的 Thought / Action】")
    for i, step in enumerate(trace, 1):
        print(f"\n──── 第 {i} 步 ────")
        print(step)

    print("\n" + "=" * 60)
    print(f"最终答案：{answer}")
    print(f"\n整理后的目录 {SANDBOX_ROOT}：")
    for p in sorted(SANDBOX_ROOT.iterdir()):
        if p.is_dir():
            inner = ", ".join(x.name for x in sorted(p.iterdir()))
            print(f"  [目录] {p.name}/  ->  {inner}")
        else:
            print(f"  [文件] {p.name}")
    print("=" * 60)


if __name__ == "__main__":
    main()
