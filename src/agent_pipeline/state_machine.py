"""显式状态机：定义流水线阶段、转移与合法动作。"""

from __future__ import annotations

from dataclasses import dataclass

STAGES = (
    "plan",
    "human_approval",
    "code",
    "review",
    "fix",
    "test",
    "done",
    "needs_human",
    "error",
)

VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "plan": ("human_approval", "needs_human", "error"),
    "human_approval": ("code", "needs_human", "error"),
    "code": ("review", "error"),
    "review": ("test", "fix", "done", "revision_exhausted", "error"),
    "fix": ("review", "error"),
    "test": ("done", "error"),
    "done": (),
    "needs_human": (),
    "error": (),
    "revision_exhausted": ("needs_human", "error"),
}


@dataclass(frozen=True)
class Transition:
    """一次状态转移。"""

    stage: str
    agent: str
    input: str
    reason: str = ""


class StateMachine:
    """有限状态机：校验每个转移是否合法，防止非法跳转。"""

    def __init__(self) -> None:
        self.stage: str = "plan"
        self.history: list[str] = ["plan"]

    def can_transition(self, to_stage: str) -> bool:
        if self.stage not in VALID_TRANSITIONS:
            return False
        return to_stage in VALID_TRANSITIONS[self.stage]

    def transition(self, to_stage: str) -> None:
        if not self.can_transition(to_stage):
            raise ValueError(
                f"非法状态转移: {self.stage} -> {to_stage}"
            )
        self.stage = to_stage
        self.history.append(to_stage)

    def reset(self) -> None:
        self.stage = "plan"
        self.history = ["plan"]


__all__ = ["STAGES", "VALID_TRANSITIONS", "Transition", "StateMachine"]
