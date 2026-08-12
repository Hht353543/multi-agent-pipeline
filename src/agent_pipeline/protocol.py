"""角色、提示词文件与调度协议的集中定义（唯一事实来源）。

新增角色、提示词文件或修改调度枚举时，只需修改本模块；
其余模块（prompts、validate、cli、tests）均引用这里的常量。
"""

from __future__ import annotations

#: 角色顺序（同时决定 `agent-pipeline list` 的输出顺序）
ROLES = ("orchestrator", "planner", "coder", "reviewer", "tester")

#: 提示词文件名（按调用顺序编号，必须齐全）
PROMPT_FILES = (
    "00-orchestrator.md",
    "01-planner.md",
    "02-coder.md",
    "03-reviewer.md",
    "04-tester.md",
)

#: 调度协议：stage 枚举
STAGES = ("plan", "code", "review", "fix", "test", "done")

#: 调度协议：agent 枚举
AGENTS = ("planner", "coder", "reviewer", "tester", "none")

#: 调度协议：stage 与下一接收 agent 的对应关系
STAGE_TO_AGENT = {
    "plan": "planner",
    "code": "coder",
    "review": "reviewer",
    "fix": "coder",
    "test": "tester",
    "done": "none",
}

#: 调度协议：fix→review 复审轮数上限（与 orchestrator 提示词约定一致）
MAX_REVIEW_ROUNDS = 3

#: 调度协议：单阶段 input 的推荐 token 上限（超出时按 orchestrator 规则降级）
MAX_INPUT_TOKENS = 8000

#: 各提示词文件必须包含的内容标记
REQUIRED_MARKERS = {
    "00-orchestrator.md": ("System Prompt", "工作流程", "输出 JSON", "阶段说明"),
    "01-planner.md": ("System Prompt", "需求理解", "技术选型", "验收标准", "待确认问题"),
    "02-coder.md": ("System Prompt", '"path"', '"code"', '"notes"'),
    "03-reviewer.md": ("System Prompt", '"verdict"', '"issues"', '"summary"'),
    "04-tester.md": ("System Prompt", '"run_command"', '"coverage_note"'),
}


def validate_dispatch_output(obj: object) -> list[str]:
    """校验 Orchestrator 输出的调度 JSON，返回错误列表（空列表表示通过）。"""
    errors: list[str] = []

    if not isinstance(obj, dict):
        return ["调度输出必须是 JSON 对象"]

    stage = obj.get("stage")
    if stage not in STAGES:
        errors.append(f"stage 必须是 {STAGES} 之一，当前为: {stage!r}")

    agent = obj.get("agent")
    if agent not in AGENTS:
        errors.append(f"agent 必须是 {AGENTS} 之一，当前为: {agent!r}")

    if stage in STAGES and agent in AGENTS:
        expected = STAGE_TO_AGENT[stage]
        if agent != expected:
            errors.append(f"stage={stage!r} 时 agent 应为 {expected!r}，当前为: {agent!r}")

    for field in ("input", "reason"):
        value = obj.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} 必须是非空字符串")

    if "fix_context" in obj:
        value = obj["fix_context"]
        if not isinstance(value, str) or not value.strip():
            errors.append("fix_context 存在时必须是非空字符串")

    return errors
