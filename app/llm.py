"""LLM 客户端：统一封装对 DeepSeek 的调用。

Agent 的每一次「思考」「回答」，本质上都是调一次大模型。
这里把调用细节封起来，别处只需 `chat(messages)` 一句话就能用。
"""
from openai import OpenAI

from app.config import settings

# 全局客户端：只创建一次，别处复用
# base_url 指向 DeepSeek（它兼容 OpenAI 的接口协议，所以用同一个库）
_client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)


def chat(messages: list[dict], temperature: float = 0.0, stop: list[str] | None = None) -> str:
    """把一段对话发给模型，返回它的回复文本。

    参数：
        messages: 对话历史，形如 [{"role": "user", "content": "你好"}]
        temperature: 随机性。0 = 尽量稳定（做 Agent 需要稳定，所以默认 0）
        stop: 停止序列。模型一旦要输出这些文字就立即停止。
              用于 ReAct 循环：让模型在 Action 后停下，别自己脑补 Observation。
    """
    resp = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        temperature=temperature,
        stop=stop,
        timeout=60.0,  # 防止网络挂起让接口无限等待（默认无超时会一直卡）
    )
    return resp.choices[0].message.content
