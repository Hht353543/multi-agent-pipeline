"""Tool 层：Agent 通过工具访问资源，禁止直接触碰文件系统。

每个工具声明自己需要的权限（action + target 通配），Agent 声明自己的
权限集合；``ToolRegistry`` 在调用时强制校验，越权直接抛 ``PermissionError``。
"""

from __future__ import annotations

import fnmatch
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from agent_pipeline.types import ToolResult


@dataclass(frozen=True)
class Permission:
    """权限声明：例如 Permission("read", "documents/*")。"""

    action: str
    target: str = "*"

    def allows(self, action: str, target: str) -> bool:
        if action != self.action:
            return False
        return fnmatch.fnmatch(target, self.target)


class BaseTool(ABC):
    """工具抽象：所有副作用通过 execute 收敛。"""

    name: str = ""
    description: str = ""
    permission: Permission = Permission("read", "*")

    def __init__(self, workspace: dict[str, str] | None = None) -> None:
        # workspace 为进程内沙箱（测试/评测注入），Agent 不直接持有。
        self._workspace: dict[str, str] = workspace if workspace is not None else {}

    @abstractmethod
    def execute(
        self,
        action: str,
        target: str = "",
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        """执行工具动作；越权或失败时返回失败 ToolResult 而非抛异常。"""


class DocumentTool(BaseTool):
    """文档读写工具：read_document / write_document。"""

    name = "document"
    description = "在沙箱工作区读写文档。"
    permission = Permission("read", "documents/*")

    def execute(
        self,
        action: str,
        target: str = "",
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        if action not in ("read", "write"):
            return ToolResult(
                success=False, tool=self.name, action=action, target=target,
                error_type="unsupported_action",
                message=f"不支持的 action: {action}",
            )
        if action == "read":
            return ToolResult(
                success=True,
                tool=self.name,
                action=action,
                target=target,
                data={"content": self._workspace.get(target, "")},
            )
        if not isinstance(data, dict) or "content" not in data:
            return ToolResult(
                success=False, tool=self.name, action=action, target=target,
                error_type="validation",
                message="write 需要 data.content",
            )
        self._workspace[target] = str(data["content"])
        return ToolResult(
            success=True,
            tool=self.name,
            action=action,
            target=target,
            data={"bytes": len(str(data["content"]))},
        )


class KnowledgeTool(BaseTool):
    """知识检索工具：search_knowledge（确定性 mock，可注入知识库）。"""

    name = "knowledge"
    description = "在本地知识库中按关键字检索。"
    permission = Permission("read", "knowledge/*")

    def __init__(
        self,
        workspace: dict[str, str] | None = None,
        knowledge: dict[str, str] | None = None,
    ) -> None:
        super().__init__(workspace)
        self._knowledge: dict[str, str] = knowledge or {}

    def execute(
        self,
        action: str,
        target: str = "",
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        if action != "search":
            return ToolResult(
                success=False, tool=self.name, action=action, target=target,
                error_type="unsupported_action",
                message=f"不支持的 action: {action}",
            )
        query = str((data or {}).get("query", "")).lower()
        hits = [
            {"source": key, "content": value[:500]}
            for key, value in self._knowledge.items()
            if not query
            or query in key.lower()
            or query in value.lower()
        ]
        return ToolResult(
            success=True,
            tool=self.name,
            action=action,
            target=target,
            data={"hits": hits[:5], "total": len(hits)},
        )


class TestTool(BaseTool):
    """测试执行工具：run_tests（确定性 mock，不执行外部命令）。"""

    name = "tests"
    description = "在沙箱中“运行”测试并返回结果。"
    permission = Permission("run", "tests/*")

    def execute(
        self,
        action: str,
        target: str = "",
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        if action != "run":
            return ToolResult(
                success=False, tool=self.name, action=action, target=target,
                error_type="unsupported_action",
                message=f"不支持的 action: {action}",
            )
        return ToolResult(
            success=True,
            tool=self.name,
            action=action,
            target=target or "tests/",
            data={"passed": 1, "failed": 0, "skipped": 0},
        )


def default_tools(
    workspace: dict[str, str] | None = None,
    knowledge: dict[str, str] | None = None,
) -> dict[str, BaseTool]:
    """创建默认工具集。"""

    return {
        "document": DocumentTool(workspace),
        "knowledge": KnowledgeTool(workspace, knowledge),
        "tests": TestTool(workspace),
    }


class ToolRegistry:
    """工具注册表 + 权限矩阵。"""

    def __init__(
        self,
        tools: dict[str, BaseTool] | None = None,
        agent_permissions: dict[str, list[Permission]] | None = None,
    ) -> None:
        self._tools = tools or default_tools()
        self._permissions = agent_permissions or {}
        self._calls: list[dict[str, Any]] = []

    def call(
        self,
        agent: str,
        tool: str,
        action: str,
        target: str = "",
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        """按 Agent 权限调用工具；越权返回失败结果并记录。"""

        allowed = self._permissions.get(agent)
        allowed_any = any(
            perm.allows(action, target) for perm in (allowed or [])
        )
        record = {
            "agent": agent,
            "tool": tool,
            "action": action,
            "target": target,
            "allowed": allowed_any,
        }
        self._calls.append(record)
        impl = self._tools.get(tool)
        if impl is None:
            return ToolResult(
                success=False, tool=tool, action=action, target=target,
                error_type="unknown_tool",
                message=f"未知工具: {tool}",
            )
        if not allowed_any:
            return ToolResult(
                success=False, tool=tool, action=action, target=target,
                error_type="permission_denied",
                message=f"Agent {agent} 无权限调用 {tool}/{action}/{target}",
            )
        result = impl.execute(action, target, data)
        result.tool = tool
        return result

    def calls(self) -> list[dict[str, Any]]:
        return list(self._calls)

    def reset_calls(self) -> None:
        self._calls.clear()


def default_permissions() -> dict[str, list[Permission]]:
    """各角色的默认权限矩阵（read/write/run 三档）。"""

    return {
        "planner": [Permission("read", "*")],
        "coder": [
            Permission("read", "*"),
            Permission("write", "src/*"),
            Permission("write", "documents/*"),
            Permission("write", "tests/*"),
        ],
        "reviewer": [Permission("read", "*")],
        "tester": [
            Permission("read", "*"),
            Permission("run", "tests/*"),
        ],
        "orchestrator": [],
    }


__all__ = [
    "Permission",
    "BaseTool",
    "DocumentTool",
    "KnowledgeTool",
    "TestTool",
    "ToolRegistry",
    "default_tools",
    "default_permissions",
]
