import json

import pytest

from agent_pipeline.runner import run_pipeline


def _scripted(script):
    calls = {"n": 0}

    def call(system_prompt, user_input):
        item = script[calls["n"]]
        calls["n"] += 1
        return json.dumps(item, ensure_ascii=False)

    return call


def test_normal_pipeline_reaches_done():
    script = [
        {"stage": "code", "agent": "coder", "input": "plan", "reason": "r"},
        {"stage": "review", "agent": "reviewer", "input": "code", "reason": "r"},
        {"stage": "test", "agent": "tester", "input": "code", "reason": "r"},
        {"stage": "done", "agent": "none", "input": "summary", "reason": "r"},
    ]
    result = run_pipeline("need", _scripted(script))
    assert result["final_output"]["stage"] == "done"


def test_fix_once_reaches_done():
    script = [
        {"stage": "code", "agent": "coder", "input": "plan", "reason": "r"},
        {"stage": "review", "agent": "reviewer", "input": "code", "reason": "r"},
        {"stage": "fix", "agent": "coder", "input": "fix", "reason": "r"},
        {"stage": "review", "agent": "reviewer", "input": "new", "reason": "r"},
        {"stage": "test", "agent": "tester", "input": "code", "reason": "r"},
        {"stage": "done", "agent": "none", "input": "summary", "reason": "r"},
    ]
    result = run_pipeline("need", _scripted(script))
    assert result["final_output"]["stage"] == "done"


def test_fix_exceeding_limit_raises():
    script = [
        {"stage": "code", "agent": "coder", "input": "plan", "reason": "r"},
        {"stage": "review", "agent": "reviewer", "input": "code", "reason": "r"},
        {"stage": "fix", "agent": "coder", "input": "f1", "reason": "r"},
        {"stage": "fix", "agent": "coder", "input": "f2", "reason": "r"},
        {"stage": "fix", "agent": "coder", "input": "f3", "reason": "r"},
        {"stage": "fix", "agent": "coder", "input": "f4", "reason": "r"},
    ]
    with pytest.raises(RuntimeError, match="超过上限"):
        run_pipeline("need", _scripted(script))


def test_invalid_output_retried_once():
    calls = {"n": 0}

    def flaky(system_prompt, user_input):
        calls["n"] += 1
        if calls["n"] == 1:
            return "{bad json"
        return json.dumps(
            {
                "stage": "done",
                "agent": "none",
                "input": "summary",
                "reason": "retry-ok",
            }
        )

    result = run_pipeline("need", flaky)
    assert result["final_output"]["stage"] == "done"
    assert calls["n"] == 2


def test_always_invalid_raises():
    def always_bad(system_prompt, user_input):
        return "{bad json"

    with pytest.raises(ValueError, match="无法解析"):
        run_pipeline("need", always_bad)


def test_non_dict_json_output_raises():
    def returns_list(system_prompt, user_input):
        return "[1, 2, 3]"

    with pytest.raises(ValueError, match="必须是 JSON 对象"):
        run_pipeline("need", returns_list)
