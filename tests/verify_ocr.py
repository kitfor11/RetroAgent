"""验证 OCR 可用：用 PIL 生成一张带中文的图片，再让 PaddleOCR 认出来。

用法：venv/Scripts/python tests/verify_ocr.py

首次运行会下载 PaddleOCR 的检测/识别模型（约 15MB），需要联网。
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont

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
    return ImageFont.load_default()  # 没有中文字体就退回默认（中文会变方块）


def main() -> None:
    # 1. 生成一张「带中文」的测试图片
    img = Image.new("RGB", (900, 160), "white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), "会议纪要 2026年9月30日", fill="black", font=_load_font())
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = f.name
    img.save(img_path)

    # 2. 让 PaddleOCR 识别（懒 import：只有这个脚本才需要，不影响主程序启动）
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    result = ocr.ocr(img_path, cls=True)

    print("OCR 识别结果：")
    for page in result or []:
        for item in page:
            text, score = item[1]
            print(f"  {text}  (置信度 {score:.2f})")

    Path(img_path).unlink(missing_ok=True)  # 清理临时图片


if __name__ == "__main__":
    main()
