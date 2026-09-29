"""反思提炼：把「任务 + 轨迹」总结成可复用的技能（成功）或教训（失败）。

这是「自我进化」的核心：Agent 做完任务后，换一个「提炼器」的角色，
让模型复盘刚才的过程。
- 成功 → 提炼成技能（复用）
- 失败 → 提炼成教训（避坑）
"""
import json

from app.llm import chat
from app.skills.models import Memory, Skill

REFLECT_PROMPT = """You are a skill extractor.

Given a task and how an agent solved it, extract ONE reusable skill.

Task:
{task}

How the agent solved it:
{trace}

Output ONLY a JSON object (no other text) with these keys:
- "name": a short skill name (lowercase, words joined by dash)
- "description": what problem this skill solves
- "steps": the concrete steps to reproduce the solution
"""


def reflect(task: str, trace: list[str]) -> Skill:
    """把「任务 + 轨迹」提炼成一条技能。"""
    # 1. 把任务和轨迹填进 prompt（轨迹用空行拼接成一段文字）
    prompt = REFLECT_PROMPT.format(
        task=task,
        trace="\n\n".join(trace),
    )

    # 2. 调 LLM，得到它输出的 JSON 字符串
    raw = chat([{"role": "user", "content": prompt}])

    # 3. 把 JSON 字符串解析成 Python 字典
    data = json.loads(raw)

    # 4. 防御性规范化：模型可能把 steps 输出成 list，统一转成字符串
    steps = data["steps"]
    if isinstance(steps, list):
        steps = "\n".join(steps)

    # 5. 用字典里的值构造 Skill 对象并返回
    skill = Skill(name=data["name"], description=data["description"], steps=steps)
    return skill


REFLECT_FAILURE_PROMPT = """You are a lesson extractor.

Given a task and how an agent FAILED at it, extract ONE lesson to avoid
repeating the same mistake.

Task:
{task}

What the agent did (which failed):
{trace}

Output ONLY a JSON object (no other text) with these keys:
- "context": a short description of WHEN this lesson applies, reusing keywords from the task itself (so similar future tasks can match it)
- "lesson": what went wrong and how to avoid it
"""


def reflect_failure(task: str, trace: list[str]) -> Memory:
    """把「任务 + 失败的轨迹」提炼成一条教训。"""
    prompt = REFLECT_FAILURE_PROMPT.format(
        task=task,
        trace="\n\n".join(trace),
    )
    raw = chat([{"role": "user", "content": prompt}])
    data = json.loads(raw)
    return Memory(context=data["context"], lesson=data["lesson"])


JUDGE_PROMPT = """You are a strict evaluator.

Given a task, the agent's reasoning trace, and its final answer, did the agent
ACTUALLY complete the task?

Task:
{task}

Agent's reasoning trace:
{trace}

Agent's final answer:
{answer}

Answer "no" if:
- the agent said it could not do it, lacks the tool, or refused;
- the agent did not actually perform the task (it never used a tool where one was needed);
- the agent merely guessed or mentioned the answer as a side note (e.g. "for reference").

Otherwise answer "yes".

Output ONLY the single word "yes" or "no".
"""


def judge_success(task: str, answer: str, trace: list[str]) -> bool:
    """让模型自己判断：这个答案到底有没有真正完成任务。

    光看「有没有 Final Answer」不够——模型可能「优雅地失败」，比如老实说
    「我没有这个工具」就交差。所以把「推理轨迹」也一起交给裁判：真正的成功
    会看到它调了工具、真的动手做了；而放弃/拒绝的轨迹里没有工具调用。
    这就是「自我评估 / LLM-as-judge」，Reflexion 这类进化 Agent 的核心环节。
    """
    prompt = JUDGE_PROMPT.format(task=task, answer=answer, trace="\n\n".join(trace))
    raw = chat([{"role": "user", "content": prompt}])
    return "yes" in raw.lower()
