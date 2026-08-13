"""真实 LLM 适配器：OpenAI 兼容接口（DeepSeek 等），供 evaluation real 模式。"""

from __future__ import annotations

from typing import Callable


def make_real_call(api_key: str) -> Callable[[str, str], str]:
    """构造 (user_input, system_prompt) -> str 的同步调用器。"""

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/",
        timeout=120.0,
    )

    def call(user_input: str, system_prompt: str) -> str:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    return call


__all__ = ["make_real_call"]
