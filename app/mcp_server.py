"""MCP server：把 Agent 的工具开放给任何 MCP 客户端。

MCP（Model Context Protocol）像 AI 工具的「USB 接口」——
只要写成 MCP server，任何 MCP 客户端（Claude Desktop 等）都能直接调用。

这里复用 app/agent/tools.py 里已经注册的工具，不重写：
把 TOOLS 注册表里的每个函数，逐一注册成 MCP 工具。
"""
from mcp.server.fastmcp import FastMCP

from app.agent.tools import TOOLS

# 创建 MCP server，起个名字（客户端会看到这个名字）
mcp = FastMCP("RetroAgent")

# 把工具注册表里的每个工具注册成 MCP 工具
# mcp.tool() 返回一个装饰器，作用在函数上；FastMCP 会自动读取函数名、
# 类型注解和 docstring，生成工具的 schema 和描述
for name, func in TOOLS.items():
    mcp.tool()(func)


if __name__ == "__main__":
    # 启动 server，默认用 stdio（标准输入输出）传输——MCP 最常用的本地通信方式
    mcp.run()
