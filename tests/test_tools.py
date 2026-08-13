"""Tool 层与权限矩阵测试。"""


from agent_pipeline.tools import (
    DocumentTool,
    KnowledgeTool,
    Permission,
    ToolRegistry,
    default_permissions,
    default_tools,
)


def test_permission_matching():
    perm = Permission("write", "src/*")
    assert perm.allows("write", "src/main.py")
    assert not perm.allows("write", "knowledge/a.txt")
    assert not perm.allows("read", "src/main.py")


def test_document_tool_write_and_read():
    tool = DocumentTool()
    result = tool.execute("write", "src/a.py", {"content": "print(1)"})
    assert result.success is True
    assert tool.execute("read", "src/a.py").data["content"] == "print(1)"


def test_knowledge_tool_search():
    tool = KnowledgeTool(knowledge={"世界观.md": "灵气复苏"})
    result = tool.execute("search", data={"query": "灵气"})
    assert result.success is True
    assert result.data["total"] == 1


def test_coder_write_allowed_but_reviewer_denied():
    tools = ToolRegistry(default_tools(), default_permissions())
    ok = tools.call("coder", "document", "write", "src/a.py", {"content": "x"})
    assert ok.success is True
    denied = tools.call(
        "reviewer", "document", "write", "src/a.py", {"content": "x"}
    )
    assert denied.success is False
    assert denied.error_type == "permission_denied"


def test_unknown_tool_returns_failure():
    tools = ToolRegistry(default_tools(), default_permissions())
    result = tools.call("coder", "nope", "read")
    assert result.success is False
    assert result.error_type == "unknown_tool"


def test_unknown_agent_denied_by_default():
    tools = ToolRegistry(default_tools(), {})
    result = tools.call("ghost", "document", "read", "a")
    assert result.error_type == "permission_denied"


def test_tester_can_run_tests():
    tools = ToolRegistry(default_tools(), default_permissions())
    result = tools.call("tester", "tests", "run", "tests/")
    assert result.success is True


def test_planner_read_only():
    tools = ToolRegistry(default_tools(), default_permissions())
    result = tools.call("planner", "document", "write", "a", {"content": "x"})
    assert result.error_type == "permission_denied"
