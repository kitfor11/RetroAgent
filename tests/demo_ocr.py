"""OCR 文件整理演示：让 Agent「看图识字」、按内容归档。

用法：venv/Scripts/python tests/demo_ocr.py

对比 demo_files.py（按扩展名分类）：这次文件名是看不出内容的 scan.png，
Agent 必须用 OCR 工具读出图片里的字，才知道它是「会议纪要」并按内容归档。
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows 控制台默认 GBK，中文会乱码/报错；统一切成 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw, ImageFont

from app.agent.react_loop import run
from app.agent.tools import SANDBOX_ROOT

# Windows 自带的中文字体（按常见程度排列，取第一个存在的）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
]


def _load_font(size: int = 48):
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def setup() -> None:
    """清空沙盒，只铺一张「内容藏在图里」的扫描件：文件名看不出是啥。"""
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT)
    SANDBOX_ROOT.mkdir()
    img = Image.new("RGB", (900, 160), "white")
    ImageDraw.Draw(img).text((20, 50), "会议纪要 2026年9月30日", fill="black", font=_load_font())
    img.save(SANDBOX_ROOT / "scan.png")


def main() -> None:
    setup()
    print("=" * 60)
    print("RetroAgent OCR 文件整理演示（看图识字 + CoT）")
    print("=" * 60)
    print(f"沙盒目录：{SANDBOX_ROOT}（只有一张文件名看不出内容的 scan.png）\n")

    task = (
        f"整理目录 {SANDBOX_ROOT}：里面有一张扫描件图片，请用 OCR 工具读出图片里的文字，"
        "判断它属于哪类文件，然后移动到对应的分类子目录（会议相关就放进 meeting/）。"
    )

    print(f"任务：{task}\n")
    print("-" * 60)
    answer, trace = run(task, max_steps=10)

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
