"""轻量多 Agent 流水线执行器（可选模块，不改变现有 CLI/API）。

该模块不直接连接任何 LLM Provider，也不涉及 API 密钥；
调用方通过注入的 ``call_llm(system_prompt, user_input) -> str`` 提供模型调用能力，
因此可以用假实现做单元测试，也可以由集成方对接任意 Provider。
"""

from __future__ import annotations

from typing import Callable

from agent_pipeline.prompts import load_prompts
from agent_pipeline.protocol import MAX_REVIEW_ROUNDS, validate_dispatch_output
from agent_pipeline.validate import parse_json_object

_MAX_ITERATIONS = 100


def run_pipeline(
    user_request: str,
    call_llm: Callable[[str, str], str],
) -> dict[str, object]:
    """运行 plan→code→review（fix→review，最多 3 轮）→test→done 流水线。

    :param user_request: 用户需求文本
    :param call_llm: 模型调用函数，参数为 (system_prompt, user_input)
    :return: {"final_output": 总控最终输出, "transcript": 全部调度记录}
    :raises ValueError: Agent 输出无法解析或未通过协议校验
    :raises RuntimeError: fix 超过轮数上限或流水线未在安全迭代次数内结束
    """
    prompts = load_prompts()
    current: dict[str, object] = {
        "stage": "plan",
        "agent": "planner",
        "input": user_request,
        "reason": "启动流水线",
    }
    transcript: list[dict[str, object]] = []
    fix_rounds = 0

    for _ in range(_MAX_ITERATIONS):
        stage = current["stage"]
        agent = current["agent"]
        assert isinstance(stage, str)
        assert isinstance(agent, str)
        transcript.append(current)

        if stage == "done":
            return {"final_output": current, "transcript": transcript}
        if agent == "none":
            raise ValueError(f"stage={stage!r} 时 agent 不应为 none")

        obj = _ask_with_retry(
            prompts, agent, str(current["input"]), call_llm
        )

        if obj["stage"] == "fix":
            fix_rounds += 1
            if fix_rounds > MAX_REVIEW_ROUNDS:
                raise RuntimeError(f"fix 轮数超过上限 {MAX_REVIEW_ROUNDS}")
        current = obj

    raise RuntimeError(f"流水线未在 {_MAX_ITERATIONS} 次调度内结束")


def _ask_with_retry(
    prompts: dict[str, str],
    agent: str,
    user_input: str,
    call_llm: Callable[[str, str], str],
) -> dict[str, object]:
    """调用 Agent；输出无效时携带错误信息重试一次，仍失败则抛出 ValueError。"""
    try:
        return _ask_agent(prompts, agent, user_input, call_llm)
    except ValueError as exc:
        retry_input = (
            f"{user_input}\n\n【输出无效，请重新输出修正后的 JSON】\n错误：{exc}"
        )
        return _ask_agent(prompts, agent, retry_input, call_llm)


def _ask_agent(
    prompts: dict[str, str],
    agent: str,
    user_input: str,
    call_llm: Callable[[str, str], str],
) -> dict[str, object]:
    text = call_llm(prompts[agent], user_input)
    try:
        obj = parse_json_object(text)
    except ValueError as exc:
        raise ValueError(f"Agent {agent!r} 输出无法解析: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"Agent {agent!r} 输出必须是 JSON 对象")
    errors = validate_dispatch_output(obj)
    if errors:
        raise ValueError(f"Agent {agent!r} 输出未通过校验: {'；'.join(errors)}")
    return obj
