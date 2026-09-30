"""ReAct 循环：Agent 的「想一步 → 动一步 → 看一步」大脑。

流程：把任务发给模型 → 模型要么说「我要调工具」，要么说「我做完了」。
- 调工具：解析出工具名和参数 → 执行 → 把结果（Observation）塞回对话 → 再来一轮。
- 做完了：返回 Final Answer，循环结束。
"""
import inspect
import re

from app.agent.tools import call_tool, TOOLS
from app.llm import chat


def _build_tool_list() -> str:
    """把已注册的工具拼成清单文字，告诉模型「你有哪些手、每只手要什么参数」。

    用 inspect.signature 自动读取每个函数的真实参数名（而不是写死 text），
    这样以后加新工具（如 move_file(src, dst)）不用再改这里。
    """
    lines = []
    for name, func in TOOLS.items():
        params = ", ".join(inspect.signature(func).parameters)
        lines.append(f"- {name}({params}): {func.__doc__.strip()}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are an agent that solves a task by thinking step by step (chain of thought).

Before every action, write out your reasoning in a "Thought:" line — this is your chain of thought.

You can use these tools:
{_build_tool_list()}

Follow these rules:
1. Output a "Thought:" line explaining what you'll do next and why.
2. Output EXACTLY one Action line in this format:
   Action: tool_name(arg1="value", arg2="value")
3. STOP after the Action line — do NOT write "Observation:" yourself; you will receive the real Observation and then decide your next step.
4. When you have the final answer, output:
   Final Answer: <the answer>
"""


def run(
    task: str,
    max_steps: int = 5,
    lessons: list | None = None,
    reference: str | None = None,
) -> tuple[str | None, list[str]]:
    """执行一个任务，走 ReAct 循环。

    返回 (最终答案, 轨迹)：
    - 成功：answer 是答案文本
    - 失败：answer 为 None（超步数 / 输出无法解析 / 调了不存在的工具）
    轨迹是每一步模型输出的列表，供「反思提炼」当素材——回顾「我刚才怎么做的」。

    lessons 是检索到的历史教训（注入 prompt 避坑）；reference 是检索到的
    历史技能步骤（注入 prompt 当参考做法）——两者合起来就是 RAG 的「增强」。
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if reference:
        # RAG 的「增强」：把检索到的历史技能作为参考做法注入，让模型结合参考生成
        messages.append({
            "role": "system",
            "content": f"Relevant past experience (use as reference, adapt to this task):\n{reference}",
        })
    if lessons:
        # 把历史教训作为额外的 system 消息注入，提醒 agent 别踩同样的坑
        tips = "\n".join(f"- {m.lesson}" for m in lessons)
        messages.append({"role": "system", "content": f"Past lessons to avoid:\n{tips}"})

    messages.append({"role": "user", "content": task})
    trace: list[str] = []

    for _ in range(max_steps):
        # stop=["Observation:"] 是关键安全网：模型想「自己脑补 Observation」时会被截断，
        # 逼它把真实观察交给我们来执行工具，而不是在脑子里演完整个流程。
        output = chat(messages, stop=["Observation:"])
        trace.append(output)  # 记下这一步的「思考 + 动作」

        if "Final Answer:" in output:
            answer = output.split("Final Answer:", 1)[1].strip()
            return answer, trace

        match = re.search(r'Action:\s*(\w+)\((.*)\)', output)
        if not match:
            # 模型没按格式输出 Action，无法解析，当作失败
            return None, trace

        tool_name = match.group(1)
        # 把 arg1="v1", arg2="v2" 解析成 {arg1: "v1", arg2: "v2"}
        args = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', match.group(2)))

        # 执行工具，把结果作为 Observation 追加进对话，继续下一轮
        try:
            result = call_tool(tool_name, args)
        except (ValueError, TypeError):
            # 工具名不存在 / 参数没给对——都是「调用姿势错了」，记成教训的失败
            return None, trace

        messages.append({"role": "assistant", "content": output})
        messages.append({"role": "user", "content": f"Observation: {result}"})

    return None, trace  # 达到最大步数仍未完成
