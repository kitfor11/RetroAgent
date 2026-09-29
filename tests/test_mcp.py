"""MCP server 测试：用 MCP 客户端连接我们的 server，列出工具并调用。

用法：venv/Scripts/python tests/test_mcp.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def main() -> None:
    # 用 stdio 方式启动我们的 MCP server 进程：
    # 客户端启动 server 子进程，通过标准输入输出和它通信
    server_params = StdioServerParameters(
        command=str(PROJECT_ROOT / "venv" / "Scripts" / "python.exe"),
        args=["-m", "app.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 列出 server 提供的工具
            tools = await session.list_tools()
            print("MCP server 提供的工具:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            # 调用一个工具
            result = await session.call_tool("count_words", {"text": "hello world"})
            print("\n调用 count_words('hello world'):")
            for item in result.content:
                print(f"  -> {item.text}")


if __name__ == "__main__":
    asyncio.run(main())
