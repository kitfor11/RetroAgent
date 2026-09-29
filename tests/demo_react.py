"""演示脚本：把 ReAct 循环的每一步「想→动→看」完整打印出来。

用法：venv/Scripts/python tests/demo_react.py
调试 Agent 时，能看到中间过程非常重要——不然它错了你都不知道错在哪一步。
"""
import re
import sys
from pathlib import Path

# 把项目根目录加入模块搜索路径，这样无论从哪运行都能 import 到 app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.react_loop import SYSTEM_PROMPT
from app.agent.tools import call_tool
from app.llm import chat


def demo(task: str) -> None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for step in range(6):
        output = chat(messages)
        print(f"━━━━━━ Step {step + 1} ━━━━━━")
        print(output)
        print()

        if "Final Answer:" in output:
            print(">>> 循环结束：得到最终答案")
            break

        # 解析 Action 并执行工具
        m = re.search(r'Action:\s*(\w+)\(text="(.*?)"\)', output)
        name, val = m.group(1), m.group(2)
        result = call_tool(name, {"text": val})

        messages.append({"role": "assistant", "content": output})
        messages.append({"role": "user", "content": f"Observation: {result}"})


if __name__ == "__main__":
    # 这个任务需要「先反转，再转大写」，会用到两个工具，展示多步循环
    demo("Reverse the text 'abc', then convert the result to uppercase")
