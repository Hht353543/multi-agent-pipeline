from agent_pipeline.protocol import validate_dispatch_output


def test_valid_dispatch_output():
    obj = {
        "stage": "plan",
        "agent": "planner",
        "input": "需求",
        "reason": "开始规划",
    }
    assert validate_dispatch_output(obj) == []


def test_invalid_stage_and_agent():
    obj = {"stage": "bad", "agent": "ghost", "input": "x", "reason": "r"}
    errors = validate_dispatch_output(obj)
    assert any("stage" in e for e in errors)
    assert any("agent" in e for e in errors)


def test_stage_agent_mismatch():
    obj = {
        "stage": "plan",
        "agent": "coder",
        "input": "x",
        "reason": "r",
    }
    errors = validate_dispatch_output(obj)
    assert any("agent 应为" in e for e in errors)


def test_missing_input_and_reason():
    obj = {"stage": "plan", "agent": "planner", "input": "", "reason": None}
    errors = validate_dispatch_output(obj)
    assert sum("必须是非空字符串" in e for e in errors) == 2


def test_optional_fix_context():
    obj = {
        "stage": "fix",
        "agent": "coder",
        "input": "x",
        "reason": "r",
        "fix_context": "issues + files",
    }
    assert validate_dispatch_output(obj) == []
    bad = dict(obj, fix_context="")
    assert any("fix_context" in e for e in validate_dispatch_output(bad))


def test_non_dict_output():
    assert validate_dispatch_output(["not", "a", "dict"])
