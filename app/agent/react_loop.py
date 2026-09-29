"""ReAct 循环：Agent 的「想一步 → 动一步 → 看一步」大脑。

流程：把任务发给模型 → 模型要么说「我要调工具」，要么说「我做完了」。
- 调工具：解析出工具名和参数 → 执行 → 把结果（Observation）塞回对话 → 再来一轮。
- 做完了：返回 Final Answer，循环结束。
"""
import re

from app.agent.tools import call_tool, TOOLS
from app.llm import chat


def _build_tool_list() -> str:
    """把已注册的工具拼成清单文字，告诉模型「你有哪些手」。"""
    lines = []
    for name, func in TOOLS.items():
        lines.append(f"- {name}(text): {func.__doc__.strip()}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are an agent that solves a task by reasoning step by step.

You can use these tools:
{_build_tool_list()}

Follow these rules:
1. First think (Thought) about what to do.
2. If you need a tool, output EXACTLY one line in this format:
   Action: tool_name(text="the input")
3. You will then receive an Observation. Use it to decide your next step.
4. When you have the final answer, output:
   Final Answer: <the answer>
"""


def run(
    task: str,
    max_steps: int = 5,
    lessons: list | None = None,
) -> tuple[str | None, list[str]]:
    """执行一个任务，走 ReAct 循环。

    返回 (最终答案, 轨迹)：
    - 成功：answer 是答案文本
    - 失败：answer 为 None（超步数 / 输出无法解析 / 调了不存在的工具）
    轨迹是每一步模型输出的列表，供「反思提炼」当素材——回顾「我刚才怎么做的」。

    lessons 是检索到的历史教训，会注入进 prompt，让 agent 提前避坑。
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if lessons:
        # 把历史教训作为额外的 system 消息注入，提醒 agent 别踩同样的坑
        tips = "\n".join(f"- {m.lesson}" for m in lessons)
        messages.append({"role": "system", "content": f"Past lessons to avoid:\n{tips}"})

    messages.append({"role": "user", "content": task})
    trace: list[str] = []

    for _ in range(max_steps):
        output = chat(messages)
        trace.append(output)  # 记下这一步的「思考 + 动作」

        if "Final Answer:" in output:
            answer = output.split("Final Answer:", 1)[1].strip()
            return answer, trace

        match = re.search(r'Action:\s*(\w+)\(text="(.*?)"\)', output)
        if not match:
            # 模型没按格式输出 Action，无法解析，当作失败
            return None, trace

        tool_name = match.group(1)
        text_value = match.group(2)

        # 执行工具，把结果作为 Observation 追加进对话，继续下一轮
        try:
            result = call_tool(tool_name, {"text": text_value})
        except ValueError:
            # 调用了不存在的工具——这正是要记成「教训」的失败
            return None, trace

        messages.append({"role": "assistant", "content": output})
        messages.append({"role": "user", "content": f"Observation: {result}"})

    return None, trace  # 达到最大步数仍未完成
