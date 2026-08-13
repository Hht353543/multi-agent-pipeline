"""结构化类型：Agent 请求/响应、计划、草稿、审校、工具结果与流水线结果。

Project A 从“纯 dict 协议校验”升级为 Pydantic 结构化输出。
调度协议（stage/agent/input/reason）继续以 ``agent_pipeline.protocol``
为唯一事实源；本模块只承载各 Agent 的领域产物。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Model(BaseModel):
    """Pydantic v1/v2 兼容基类：统一提供 v2 风格序列化 API。"""

    def model_dump(self) -> dict[str, Any]:
        dump = getattr(super(), "model_dump", None)
        if dump is not None:
            return dict(dump())
        return dict(self.dict())

    def model_dump_json(self) -> str:
        dump = getattr(super(), "model_dump_json", None)
        if dump is not None:
            return str(dump())
        return str(self.json())


# ---------- Agent 基础 ----------


class AgentRequest(Model):
    """Agent 请求封装。"""

    run_id: str = ""
    agent: str = ""
    input: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(Model):
    """Agent 统一响应基类。"""

    success: bool = True
    agent: str = ""
    run_id: str = ""
    message: str = ""
    error_type: str = ""
    telemetry: dict[str, Any] = Field(default_factory=dict)


# ---------- 领域产物 ----------


class Plan(Model):
    """Planner 输出：可执行开发计划。"""

    summary: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    workflow: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class CodeFile(Model):
    """Coder 输出中的单个文件。"""

    path: str = ""
    language: str = ""
    code: str = ""
    notes: str = ""


class Draft(Model):
    """Coder 输出：文件清单与代码。"""

    files: list[CodeFile] = Field(default_factory=list)
    notes: str = ""


class ReviewIssue(Model):
    """Reviewer 输出中的单个问题。"""

    severity: Literal["critical", "major", "minor"] = "major"
    location: str = ""
    description: str = ""
    suggestion: str = ""


class ReviewResult(Model):
    """Reviewer 输出：裁决与问题列表。"""

    verdict: Literal["pass", "needs_fix"] = "pass"
    score: int = Field(default=0, ge=0, le=100)
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "pass"


class TestResult(Model):
    """Tester 输出。"""

    files: list[CodeFile] = Field(default_factory=list)
    run_command: str = ""
    coverage_note: str = ""


class ToolResult(Model):
    """统一工具调用结果。"""

    success: bool = True
    tool: str = ""
    action: str = ""
    target: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    error_type: str = ""


class ApprovalDecision(Model):
    """Human-in-the-loop 审批结果。"""

    status: Literal["APPROVED", "REJECTED", "EDITED"] = "APPROVED"
    edited_plan: Plan | None = None
    comment: str = ""


# ---------- 流水线结果 ----------


class PipelineResult(Model):
    """一次完整 Agent 流水线运行的结果。"""

    run_id: str = ""
    status: Literal[
        "success", "error", "rejected", "needs_human", "revision_exhausted"
    ] = "success"
    message: str = ""
    final_dispatch: dict[str, Any] | None = None
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    plan: Plan | None = None
    draft: Draft | None = None
    review: ReviewResult | None = None
    test: TestResult | None = None
    telemetry: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


__all__ = [
    "AgentRequest",
    "AgentResponse",
    "Plan",
    "CodeFile",
    "Draft",
    "ReviewIssue",
    "ReviewResult",
    "TestResult",
    "ToolResult",
    "ApprovalDecision",
    "PipelineResult",
]
