"""遥测：token 估算、成本计算与步骤级 trace。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


def estimate_tokens(text: str) -> int:
    """保守估算 token 数：中日韩字符按 1 字符 ≈ 1 token，其余按 4 字符 ≈ 1 token。"""

    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other = len(text) - cjk
    return cjk + (other + 3) // 4


@dataclass
class StepTrace:
    """单个 Agent 步骤的 trace 记录。"""

    stage: str = ""
    agent: str = ""
    status: str = "ok"
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    retries: int = 0
    error: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "agent": self.agent,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost": round(self.estimated_cost, 6),
            "retries": self.retries,
            "error": self.error,
            "tool_calls": self.tool_calls,
        }


class Telemetry:
    """运行级遥测：run_id / trace_id / steps / 汇总。"""

    def __init__(
        self,
        run_id: str = "",
        trace_id: str = "",
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
    ) -> None:
        self.run_id = run_id
        self.trace_id = trace_id or f"trace-{run_id or 'unknown'}"
        self.steps: list[StepTrace] = []
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self.started_at = time.time()

    def start_step(self, stage: str, agent: str) -> StepTrace:
        step = StepTrace(stage=stage, agent=agent)
        self.steps.append(step)
        return step

    def record_llm(
        self,
        step: StepTrace,
        prompt: str,
        output: str,
        duration_ms: float,
    ) -> None:
        step.duration_ms += duration_ms
        step.input_tokens += estimate_tokens(prompt)
        step.output_tokens += estimate_tokens(output)
        step.estimated_cost += (
            step.input_tokens / 1000 * self.cost_per_1k_input
            + step.output_tokens / 1000 * self.cost_per_1k_output
        )

    def record_tool_calls(
        self, step: StepTrace, calls: list[dict[str, Any]]
    ) -> None:
        step.tool_calls.extend(calls)

    def fail_step(self, step: StepTrace, error: str, retries: int = 0) -> None:
        step.status = "error"
        step.error = error
        step.retries = retries

    def summary(self) -> dict[str, Any]:
        total_ms = sum(s.duration_ms for s in self.steps)
        total_in = sum(s.input_tokens for s in self.steps)
        total_out = sum(s.output_tokens for s in self.steps)
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "steps": [s.to_dict() for s in self.steps],
            "total_duration_ms": round(total_ms, 2),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_tokens": total_in + total_out,
            "estimated_cost": round(
                sum(s.estimated_cost for s in self.steps), 6
            ),
            "llm_calls": len(self.steps),
            "errors": [s.error for s in self.steps if s.error],
            "retries": sum(s.retries for s in self.steps),
        }


__all__ = ["estimate_tokens", "StepTrace", "Telemetry"]
