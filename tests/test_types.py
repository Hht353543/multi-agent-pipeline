"""结构化类型测试。"""

from agent_pipeline.types import (
    ApprovalDecision,
    Draft,
    Plan,
    ReviewResult,
    ToolResult,
)


def test_plan_roundtrip():
    plan = Plan(
        summary="计划",
        tech_stack=["python"],
        acceptance_criteria=["pytest 通过"],
        pending_questions=["输入格式？"],
    )
    restored = Plan(**plan.model_dump())
    assert restored.summary == "计划"
    assert restored.pending_questions == ["输入格式？"]


def test_review_passed_property():
    passed = ReviewResult(verdict="pass", score=90)
    failed = ReviewResult(verdict="needs_fix", score=50)
    assert passed.passed is True
    assert failed.passed is False


def test_draft_and_tool_result_serialize():
    draft = Draft(files=[], notes="n")
    assert "notes" in draft.model_dump()
    result = ToolResult(success=False, tool="x", error_type="denied")
    assert result.success is False


def test_approval_decision_variants():
    assert ApprovalDecision(status="APPROVED").status == "APPROVED"
    assert ApprovalDecision(status="REJECTED").status == "REJECTED"
    assert ApprovalDecision(status="EDITED").status == "EDITED"
