"""Agent 抽象与角色实现。

所有 Agent 继承 :class:`BaseAgent`；统一生命周期为
``validate_input -> _run -> validate_output``，由编排器通过
:class:`AgentRegistry` 创建实例，避免 ``if agent == ...`` 硬编码。
Agent 只能通过注入的 :class:`ToolRegistry` 访问资源。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from agent_pipeline.telemetry import StepTrace, Telemetry
from agent_pipeline.tools import ToolRegistry
from agent_pipeline.types import (
    AgentRequest,
    AgentResponse,
    CodeFile,
    Draft,
    Plan,
    ReviewIssue,
    ReviewResult,
    TestResult,
    ToolResult,
)


class AgentError(Exception):
    """Agent 统一错误（含类型与步骤信息）。"""

    def __init__(
        self,
        agent: str,
        error_type: str,
        message: str,
        run_id: str = "",
    ) -> None:
        super().__init__(message)
        self.agent = agent
        self.error_type = error_type
        self.message = message
        self.run_id = run_id


@dataclass
class AgentContext:
    """Agent 运行上下文：显式携带请求、工具、遥测与中间状态。"""

    run_id: str
    request: AgentRequest
    tools: ToolRegistry
    telemetry: Telemetry
    step: StepTrace
    user_request: str = ""
    plan: Plan | None = None
    draft: Draft | None = None
    review: ReviewResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Agent 抽象基类。"""

    name: str = "base"
    role: str = ""

    def __init__(
        self,
        call_llm: Callable[[str, str], str] | None = None,
    ) -> None:
        # call_llm 可能由编排器注入；缺省时抛明确错误，避免静默失败。
        self.call_llm = call_llm

    async def execute(self, ctx: AgentContext) -> AgentResponse:
        """统一执行入口：校验输入 -> 运行 -> 校验输出。"""

        try:
            self.validate_input(ctx)
            result = await self._run(ctx)
            self.validate_output(ctx, result)
            return result
        except AgentError:
            raise
        except Exception as exc:
            raise AgentError(
                self.name, "unknown", str(exc), run_id=ctx.run_id
            ) from exc

    @abstractmethod
    async def _run(self, ctx: AgentContext) -> AgentResponse:
        """Agent 核心逻辑。"""

    def validate_input(self, ctx: AgentContext) -> None:
        if not ctx.request.input.strip():
            raise AgentError(
                self.name,
                "validation",
                "input 为空",
                run_id=ctx.run_id,
            )

    def validate_output(self, ctx: AgentContext, result: AgentResponse) -> None:
        return

    def call_tool(
        self,
        ctx: AgentContext,
        tool: str,
        action: str,
        target: str = "",
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        """唯一工具入口：记录调用并强制权限校验。"""

        result = ctx.tools.call(
            self.name, tool, action, target, data
        )
        return result

    def ask_llm(self, ctx: AgentContext, prompt: str) -> str:
        """统一 LLM 调用：经编排器封装的遥测/重试闭包。"""

        if self.call_llm is None:
            raise AgentError(
                self.name,
                "llm",
                "未注入 LLM 调用器",
                run_id=ctx.run_id,
            )
        return self.call_llm(ctx.request.input, prompt)


# ---------- 角色实现 ----------


def _safe_json(text: str) -> dict[str, Any]:
    """解析模型输出中的 JSON 对象（带常见容错）。"""

    import json
    import re

    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        stripped = stripped[start : end + 1]
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        raise AgentError("", "parse", f"无法解析 JSON: {text[:200]}")
    if not isinstance(obj, dict):
        raise AgentError("", "parse", "模型输出不是 JSON 对象")
    return obj


class PlannerAgent(BaseAgent):
    """需求分析 Agent：把用户需求拆解为可执行计划。"""

    name = "planner"
    role = "需求分析 Agent"

    async def _run(self, ctx: AgentContext) -> AgentResponse:
        prompt = f"请为以下需求制定开发计划：\n{ctx.request.input}"
        text = self.ask_llm(ctx, prompt)
        data = _safe_json(text)
        plan = Plan(
            summary=str(data.get("summary", "")),
            tech_stack=[str(x) for x in data.get("tech_stack", [])],
            modules=[str(x) for x in data.get("modules", [])],
            workflow=str(data.get("workflow", "")),
            acceptance_criteria=[
                str(x) for x in data.get("acceptance_criteria", [])
            ],
            pending_questions=[
                str(x) for x in data.get("pending_questions", [])
            ],
            assumptions=[str(x) for x in data.get("assumptions", [])],
        )
        return AgentResponse(
            success=True,
            agent=self.name,
            run_id=ctx.run_id,
            telemetry={"plan": plan.model_dump()},
        )


class CoderAgent(BaseAgent):
    """代码生成 Agent：按计划生成文件，通过工具写沙箱。"""

    name = "coder"
    role = "代码生成 Agent"

    async def _run(self, ctx: AgentContext) -> AgentResponse:
        prompt = f"请按以下计划生成代码：\n{ctx.request.input}"
        text = self.ask_llm(ctx, prompt)
        data = _safe_json(text)
        files = []
        for item in data.get("files", []):
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            code = str(item.get("code", ""))
            language = str(item.get("language", ""))
            files.append(
                {
                    "path": path,
                    "language": language,
                    "code": code,
                }
            )
            # 通过 Tool 写入沙箱，Agent 不直接访问文件系统
            if path:
                self.call_tool(
                    ctx,
                    "document",
                    "write",
                    target=path,
                    data={"content": code},
                )
        draft = Draft(
            files=[CodeFile(**item) for item in files],
            notes=str(data.get("notes", "")),
        )
        return AgentResponse(
            success=True,
            agent=self.name,
            run_id=ctx.run_id,
            telemetry={"draft": draft.model_dump()},
        )


class ReviewerAgent(BaseAgent):
    """代码审校 Agent：裁决 pass / needs_fix，输出结构化问题。"""

    name = "reviewer"
    role = "代码审校 Agent"

    async def _run(self, ctx: AgentContext) -> AgentResponse:
        prompt = f"请审校以下代码：\n{ctx.request.input}"
        text = self.ask_llm(ctx, prompt)
        data = _safe_json(text)
        verdict = data.get("verdict", "needs_fix")
        if verdict not in ("pass", "needs_fix"):
            verdict = "needs_fix"
        issues = []
        for item in data.get("issues", []):
            if not isinstance(item, dict):
                continue
            issues.append(
                ReviewIssue(
                    severity=str(
                        item.get("severity", "major")
                    ),  # type: ignore[arg-type]
                    location=str(item.get("location", "")),
                    description=str(item.get("description", "")),
                    suggestion=str(item.get("suggestion", "")),
                )
            )
        review = ReviewResult(
            verdict=verdict,
            score=int(data.get("score", 100 if verdict == "pass" else 60)),
            issues=issues,
            summary=str(data.get("summary", "")),
        )
        return AgentResponse(
            success=True,
            agent=self.name,
            run_id=ctx.run_id,
            telemetry={"review": review.model_dump()},
        )


class TesterAgent(BaseAgent):
    """测试生成 Agent：生成测试文件并通过工具“运行”。"""

    name = "tester"
    role = "测试生成 Agent"

    async def _run(self, ctx: AgentContext) -> AgentResponse:
        prompt = f"请为以下代码生成测试：\n{ctx.request.input}"
        text = self.ask_llm(ctx, prompt)
        data = _safe_json(text)
        files = []
        for item in data.get("files", []):
            if not isinstance(item, dict):
                continue
            files.append(
                CodeFile(
                    path=str(item.get("path", "")),
                    language=str(item.get("language", "")),
                    code=str(item.get("code", "")),
                )
            )
        test_result = TestResult(
            files=files,
            run_command=str(data.get("run_command", "pytest")),
            coverage_note=str(data.get("coverage_note", "")),
        )
        self.call_tool(ctx, "tests", "run", target="tests/")
        return AgentResponse(
            success=True,
            agent=self.name,
            run_id=ctx.run_id,
            telemetry={"test": test_result.model_dump()},
        )


# ---------- 注册表与工厂 ----------


AgentFactory = Callable[..., BaseAgent]


class AgentRegistry:
    """按名称注册与创建 Agent（避免 if/elif 硬编码）。"""

    def __init__(self) -> None:
        self._factories: dict[str, AgentFactory] = {}

    def register(self, name: str, factory: AgentFactory) -> None:
        self._factories[name] = factory

    def create(self, name: str, **deps: object) -> BaseAgent:
        if name not in self._factories:
            raise KeyError(f"未知 Agent: {name}")
        return self._factories[name](**deps)

    def names(self) -> list[str]:
        return list(self._factories)


def default_registry(call_llm: Callable[[str, str], str]) -> AgentRegistry:
    """创建默认注册表并注入 LLM 调用。"""

    registry = AgentRegistry()
    registry.register("planner", lambda **kw: PlannerAgent(call_llm))
    registry.register("coder", lambda **kw: CoderAgent(call_llm))
    registry.register("reviewer", lambda **kw: ReviewerAgent(call_llm))
    registry.register("tester", lambda **kw: TesterAgent(call_llm))
    return registry


__all__ = [
    "AgentError",
    "AgentContext",
    "BaseAgent",
    "PlannerAgent",
    "CoderAgent",
    "ReviewerAgent",
    "TesterAgent",
    "AgentRegistry",
    "AgentFactory",
    "default_registry",
]
