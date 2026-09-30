"""pytest 全局配置：把项目根目录加进 sys.path，测试里才能 `import app.xxx`。

为什么需要它：pytest 默认不会自动把项目根目录放进 sys.path，
而我们的测试要从 app/ 包导入代码。加这一行后，所有测试文件共享。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
