"""OCR 引擎：让 Agent 能「读」图片里的文字（多模态的第一步）。

和 embedding 一样走「接口 + 可替换实现 + 懒加载」这套老套路：
- PaddleOCREngine：真 OCR（首次调用才 import/初始化，避免拖慢主程序启动）
- DummyOCR：没装 PaddleOCR 时的降级占位，返回提示而不是崩

抽象的价值：Agent 只依赖 `get_ocr().read_text(path)` 这一个动作，
底层换 OCR 引擎（甚至换云 API）都不用改 Agent 和工具代码。
"""
from app.config import settings


class OCR:
    """OCR 引擎接口：输入图片路径，返回识别到的文字（多行用换行拼接）。"""

    def read_text(self, image_path: str) -> str:
        raise NotImplementedError


class PaddleOCREngine(OCR):
    """PaddleOCR 实现（中文友好）。懒加载：第一次实例化才 import 和初始化。"""

    def __init__(self) -> None:
        from paddleocr import PaddleOCR
        # use_angle_cls=True 自动纠正旋转/倒置的图；lang="ch" 中英混合识别
        self._ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

    def read_text(self, image_path: str) -> str:
        result = self._ocr.ocr(image_path, cls=True)
        # result 结构：[[[box, (text, score)], ...], ...]（外层按图分页）
        lines = []
        for page in result or []:
            if not page:
                continue  # 这一页没识别到文字时 paddle 会返回 None，跳过而不是崩
            for item in page:
                lines.append(item[1][0])  # item[1] = (text, score)，取文字
        return "\n".join(lines)


class DummyOCR(OCR):
    """没装 PaddleOCR 时的降级：返回提示，不让 Agent 崩（优雅降级）。"""

    def read_text(self, image_path: str) -> str:
        return "(OCR 未安装：请 pip install paddleocr paddlepaddle)"


_ocr: OCR | None = None


def get_ocr() -> OCR:
    """全局单例工厂：按配置返回 OCR 引擎，初始化失败就降级成 Dummy。"""
    global _ocr
    if _ocr is None:
        if settings.ocr_backend == "paddle":
            try:
                _ocr = PaddleOCREngine()
            except Exception:
                _ocr = DummyOCR()
        else:
            _ocr = DummyOCR()
    return _ocr
