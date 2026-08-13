"""编排器：驱动状态机、调用 Agent、管理 HITL / 重试 / 降级 / Checkpoint。"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from agent_pipeline.agents import (
    AgentContext,
    AgentRegistry,
    BaseAgent,
    CoderAgent,
    PlannerAgent,
    ReviewerAgent,
    TesterAgent,
)
from agent_pipeline.checkpoint import CheckpointStore
from agent_pipeline.mock_provider import MockLLM
from agent_pipeline.protocol import MAX_REVIEW_ROUNDS
from agent_pipeline.state_machine import StateMachine
from agent_pipeline.telemetry import Telemetry
from agent_pipeline.tools import ToolRegistry, default_permissions, default_tools
from agent_pipeline.types import (
    AgentRequest,
    ApprovalDecision,
    Draft,
    PipelineResult,
    Plan,
    ReviewResult,
    TestResult,
)

ApprovalHandler = Callable[[Plan], ApprovalDecision]
ErrorHandler = Callable[[str, str, str], bool]


@dataclass
class OrchestratorConfig:
    """编排器配置：重试、退避、成本与阶段开关。"""

    max_retries: int = 2
    retry_base_delay: float = 0.1
    retry_max_delay: float = 2.0
    max_review_rounds: int = MAX_REVIEW_ROUNDS
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    checkpoint_store: CheckpointStore | None = None
    knowledge: dict[str, str] = field(default_factory=dict)


class Orchestrator:
    """多 Agent 流水线编排器。

    Agent 通过注册表创建；状态通过 :class:`StateMachine` 校验；
    资源访问全部走 :class:`ToolRegistry`；运行过程写入
    :class:`Telemetry` 并可选持久化到 :class:`CheckpointStore`。
    """

    def __init__(
        self,
        call_llm: Callable[[str, str], str] | None = None,
        config: OrchestratorConfig | None = None,
        workspace: dict[str, str] | None = None,
    ) -> None:
        self.call_llm = call_llm or MockLLM()
        self.config = config or OrchestratorConfig()
        self.registry = self._build_registry()
        self.tools = ToolRegistry(
            default_tools(workspace, self.config.knowledge),
            default_permissions(),
        )
        self._current_step: threading.local = threading.local()

    def _build_registry(self) -> AgentRegistry:
        registry = AgentRegistry()
        registry.register("planner", lambda **kw: PlannerAgent())
        registry.register("coder", lambda **kw: CoderAgent())
        registry.register("reviewer", lambda **kw: ReviewerAgent())
        registry.register("tester", lambda **kw: TesterAgent())
        return registry

    def _agent(self, name: str) -> BaseAgent:
        agent = self.registry.create(name)

        def _wrapped(user_input: str, prompt: str) -> str:
            ctx = getattr(self._current_step, "ctx", None)
            if ctx is None:
                raise RuntimeError("Agent 调用缺少运行上下文")
            return self._call_with_retry(
                ctx, user_input, f"system:{name}"
            )

        agent.call_llm = _wrapped
        return agent

    @staticmethod
    def _to_json(model: Any) -> str:
        """序列化为 UTF-8 JSON，避免 Pydantic v1 默认 \\uXXXX 转义。"""

        return json.dumps(model.model_dump(), ensure_ascii=False)

    def _call_with_retry(
        self, ctx: AgentContext, user_input: str, system_prompt: str
    ) -> str:
        """带指数退避重试的 LLM 调用；耗尽量时抛 AgentError。"""

        last_error = ""
        for attempt in range(self.config.max_retries + 1):
            try:
                start = time.perf_counter()
                text = self.call_llm(user_input, system_prompt)
                ctx.telemetry.record_llm(
                    ctx.step,
                    system_prompt + "\n" + user_input,
                    text,
                    (time.perf_counter() - start) * 1000,
                )
                return text
            except Exception as exc:
                last_error = str(exc)
                ctx.step.retries += 1
                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.retry_base_delay * (2**attempt),
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
        from agent_pipeline.agents import AgentError

        raise AgentError(
            ctx.request.agent,
            "llm",
            f"LLM 调用重试耗尽: {last_error}",
            run_id=ctx.run_id,
        )

    async def run(
        self,
        user_request: str,
        *,
        run_id: str | None = None,
        approve: ApprovalHandler | None = None,
        on_error: ErrorHandler | None = None,
    ) -> PipelineResult:
        """执行完整流水线；返回结构化结果而非抛异常。"""

        run_id = run_id or uuid.uuid4().hex
        telemetry = Telemetry(
            run_id=run_id,
            cost_per_1k_input=self.config.cost_per_1k_input,
            cost_per_1k_output=self.config.cost_per_1k_output,
        )
        machine = StateMachine()
        transcript: list[dict[str, Any]] = []
        plan: Plan | None = None
        draft: Draft | None = None
        review: ReviewResult | None = None
        test: TestResult | None = None
        fix_rounds = 0

        checkpoint = self.config.checkpoint_store
        if checkpoint is not None:
            saved = checkpoint.load(run_id)
            if saved:
                machine.stage = str(saved.get("stage", "plan"))
                machine.history = list(saved.get("history", ["plan"]))
                transcript = list(saved.get("transcript", []))
                plan = Plan(**saved["plan"]) if saved.get("plan") else None
                draft = (
                    Draft(**saved["draft"]) if saved.get("draft") else None
                )
                review = (
                    ReviewResult(**saved["review"])
                    if saved.get("review")
                    else None
                )
                test = (
                    TestResult(**saved["test"]) if saved.get("test") else None
                )
                fix_rounds = int(saved.get("fix_rounds", 0))

        def _checkpoint() -> None:
            if checkpoint is None:
                return
            checkpoint.save(
                run_id,
                {
                    "run_id": run_id,
                    "stage": machine.stage,
                    "history": machine.history,
                    "transcript": transcript,
                    "plan": plan.model_dump() if plan else None,
                    "draft": draft.model_dump() if draft else None,
                    "review": review.model_dump() if review else None,
                    "test": test.model_dump() if test else None,
                    "fix_rounds": fix_rounds,
                },
            )

        def _ctx(stage: str, agent: str, content: str) -> AgentContext:
            step = telemetry.start_step(stage, agent)
            request = AgentRequest(
                run_id=run_id, agent=agent, input=content
            )
            return AgentContext(
                run_id=run_id,
                request=request,
                tools=self.tools,
                telemetry=telemetry,
                step=step,
                user_request=user_request,
                plan=plan,
                draft=draft,
                review=review,
                metadata={"stage": stage},
            )

        def _set_current(ctx: AgentContext | None) -> None:
            self._current_step.ctx = ctx

        def _record_tools(ctx: AgentContext) -> None:
            """把 Agent 步骤内的工具调用写入该步骤遥测。"""

            ctx.telemetry.record_tool_calls(ctx.step, self.tools.calls())
            self.tools.reset_calls()

        def _dispatch(
            agent_name: str, stage: str, content: str, reason: str = ""
        ) -> dict[str, Any]:
            item = {
                "stage": stage,
                "agent": agent_name,
                "input": content,
                "reason": reason,
            }
            transcript.append(item)
            return item

        try:
            # ---- plan（checkpoint 已含计划时跳过）----
            if machine.stage == "plan":
                _dispatch("planner", "plan", user_request, "开始规划")
                ctx = _ctx("plan", "planner", user_request)
                _set_current(ctx)
                agent = self._agent("planner")
                response = await agent.execute(ctx)
                _set_current(None)
                _record_tools(ctx)
                plan_data = response.telemetry.get("plan", {})
                if plan_data:
                    plan = Plan(**plan_data)
                ctx.plan = plan
                _checkpoint()

                if plan and plan.pending_questions:
                    machine.transition("needs_human")
                    return PipelineResult(
                        run_id=run_id,
                        status="needs_human",
                        message="需求不明确，等待人工补充："
                        + "; ".join(plan.pending_questions),
                        transcript=transcript,
                        plan=plan,
                        telemetry=telemetry.summary(),
                    )

                # ---- human-in-the-loop ----
                if approve is not None:
                    machine.transition("human_approval")
                    _dispatch(
                        "human",
                        "human_approval",
                        self._to_json(plan) if plan else "",
                        "等待人工审批",
                    )
                    decision = approve(plan or Plan())
                    if decision.status == "REJECTED":
                        return PipelineResult(
                            run_id=run_id,
                            status="rejected",
                            message=decision.comment or "计划被人工驳回",
                            transcript=transcript,
                            plan=plan,
                            telemetry=telemetry.summary(),
                        )
                    if decision.status == "EDITED" and decision.edited_plan:
                        plan = decision.edited_plan
                    _checkpoint()

            # ---- code（plan/审批完成或断点恢复未生成代码时执行）----
            if machine.stage in ("code", "human_approval"):
                machine.transition("code")
                code_input = self._to_json(plan) if plan else user_request
                _dispatch("coder", "code", code_input, "按计划生成代码")
                ctx = _ctx("code", "coder", code_input)
                _set_current(ctx)
                response = await self._agent("coder").execute(ctx)
                _set_current(None)
                _record_tools(ctx)
                draft_data = response.telemetry.get("draft", {})
                if draft_data:
                    draft = Draft(**draft_data)
                ctx.draft = draft
                _checkpoint()

            # ---- review（code 之后第一次审校；断点停在 review 时复用恢复结果）----
            if machine.stage == "code" and review is None:
                machine.transition("review")
                review_input = (
                    self._to_json(draft) if draft else "无代码产物"
                )
                _dispatch("reviewer", "review", review_input, "审校代码")
                ctx = _ctx("review", "reviewer", review_input)
                _set_current(ctx)
                response = await self._agent("reviewer").execute(ctx)
                _set_current(None)
                _record_tools(ctx)
                review_data = response.telemetry.get("review", {})
                if review_data:
                    review = ReviewResult(**review_data)
                ctx.review = review
                _checkpoint()

            # 断点恢复且状态停在 fix 时，先回到 review 再按审校结果走
            if machine.stage == "fix":
                machine.transition("review")

            while review is not None and not review.passed:
                if fix_rounds >= self.config.max_review_rounds:
                    machine.transition("revision_exhausted")
                    return PipelineResult(
                        run_id=run_id,
                        status="revision_exhausted",
                        message=(
                            f"审校未通过且修订轮次达上限"
                            f"（{self.config.max_review_rounds}），待人工处理"
                        ),
                        transcript=transcript,
                        plan=plan,
                        draft=draft,
                        review=review,
                        telemetry=telemetry.summary(),
                    )
                fix_rounds += 1
                machine.transition("fix")
                fix_input = (
                    f"原代码：{self._to_json(draft) if draft else ''}\n"
                    f"审校意见：{self._to_json(review)}"
                )
                _dispatch("coder", "fix", fix_input, "按审校意见修复")
                ctx = _ctx("fix", "coder", fix_input)
                _set_current(ctx)
                response = await self._agent("coder").execute(ctx)
                _set_current(None)
                _record_tools(ctx)
                draft_data = response.telemetry.get("draft", {})
                if draft_data:
                    draft = Draft(**draft_data)
                ctx.draft = draft

                machine.transition("review")
                review_input = (
                    self._to_json(draft) if draft else "无代码产物"
                )
                _dispatch(
                    "reviewer",
                    "review",
                    review_input,
                    f"第 {fix_rounds} 轮复审",
                )
                ctx = _ctx("review", "reviewer", review_input)
                _set_current(ctx)
                response = await self._agent("reviewer").execute(ctx)
                _set_current(None)
                _record_tools(ctx)
                review_data = response.telemetry.get("review", {})
                if review_data:
                    review = ReviewResult(**review_data)
                ctx.review = review
                _checkpoint()

            # ---- test（checkpoint 已测试时跳过）----
            if machine.stage == "review":
                machine.transition("test")
                test_input = (
                    self._to_json(draft) if draft else "无代码产物"
                )
                _dispatch("tester", "test", test_input, "生成并运行测试")
                ctx = _ctx("test", "tester", test_input)
                _set_current(ctx)
                response = await self._agent("tester").execute(ctx)
                _set_current(None)
                _record_tools(ctx)
                test_data = response.telemetry.get("test", {})
                if test_data:
                    test = TestResult(**test_data)
                _checkpoint()

            machine.transition("done")
            final = _dispatch(
                "none", "done", "流水线完成", "全部阶段通过"
            )
            if checkpoint is not None:
                checkpoint.delete(run_id)
            return PipelineResult(
                run_id=run_id,
                status="success",
                message="流水线执行成功",
                final_dispatch=final,
                transcript=transcript,
                plan=plan,
                draft=draft,
                review=review,
                test=test,
                telemetry=telemetry.summary(),
            )
        except Exception as exc:
            if on_error is not None and on_error(
                run_id, machine.stage, str(exc)
            ):
                return PipelineResult(
                    run_id=run_id,
                    status="needs_human",
                    message=f"降级为人工处理: {exc}",
                    transcript=transcript,
                    plan=plan,
                    draft=draft,
                    review=review,
                    telemetry=telemetry.summary(),
                    error=str(exc),
                )
            return PipelineResult(
                run_id=run_id,
                status="error",
                message=str(exc),
                transcript=transcript,
                plan=plan,
                draft=draft,
                review=review,
                telemetry=telemetry.summary(),
                error=str(exc),
            )


__all__ = [
    "Orchestrator",
    "OrchestratorConfig",
    "ApprovalHandler",
    "ErrorHandler",
]
