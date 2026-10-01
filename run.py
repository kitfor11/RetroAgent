"""一键启动：检查环境 → 启动后端 → 自动打开浏览器。

用法（任选其一）：
    python run.py      # 命令行启动（Windows / macOS / Linux 通用）
    start.bat          # Windows 下直接双击

这里只做「启动前检查 + 启动 + 开浏览器」这一件事；
真正跑起来的是 app/main.py 里的 FastAPI 应用（uvicorn 去加载它）。
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# 项目根目录 = 本文件所在目录。启动前切过去，保证相对路径（.env、chroma_db 等）都找得到。
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


def fail(msg: str) -> None:
    """打印错误并退出。Windows 双击场景下停一下，别让窗口一闪而过。"""
    print(f"\n[错误] {msg}\n")
    if os.name == "nt":
        input("按回车键退出…")
    sys.exit(1)


def check_env() -> None:
    """检查 .env 是否存在、API key 是否真的填了（不能还是占位符）。"""
    env_file = ROOT / ".env"
    if not env_file.exists():
        fail("没找到 .env 文件。\n"
             "请把 .env.example 复制一份，改名为 .env，并填入 DEEPSEEK_API_KEY。")

    key = ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DEEPSEEK_API_KEY="):
            key = line.split("=", 1)[1].strip()

    # 只判断「填没填」，绝不打印 key 本身
    if not key or "你的key" in key or key.startswith("sk-在这里"):
        fail(".env 里的 DEEPSEEK_API_KEY 还是占位符，没填真实 key。")


def check_redis() -> None:
    """检查 Redis 是否在线（技能库/记忆库要用）。没起只提醒，不阻止启动。"""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, socket_connect_timeout=2)
        r.ping()
        print("✓ Redis 已连接（技能库 / 记忆库可用）")
    except Exception as e:  # noqa: BLE001 —— 连不上只是提醒，不中断
        print(f"⚠ 连不上 Redis（{type(e).__name__}）。技能库/记忆库会不可用，文档问答不受影响。")


def open_browser_when_ready(url: str, timeout: float = 60.0) -> None:
    """后台线程：等服务真的起来（/health 能通）再开浏览器，避免开早了是白页。"""
    import urllib.request

    def _open() -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                urllib.request.urlopen(url + "/health", timeout=1)
                webbrowser.open(url)
                return
            except Exception:  # noqa: BLE001 —— 还没起来就再等等
                time.sleep(0.5)

    threading.Thread(target=_open, daemon=True).start()


def main() -> None:
    print("=" * 46)
    print("  EvoAgent 一键启动")
    print("=" * 46)
    check_env()
    check_redis()

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    print(f"\n正在启动后端：{url}")
    print("启动成功后会自动打开浏览器；按 Ctrl+C 停止服务。\n")

    open_browser_when_ready(url)

    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
