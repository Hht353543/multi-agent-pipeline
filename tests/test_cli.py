import io
import json

import pytest

from agent_pipeline.cli import main
from agent_pipeline.prompts import load_prompts


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert "agent-pipeline 0.1.0" in capsys.readouterr().out


def test_list_prints_roles_in_order(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["orchestrator", "planner", "coder", "reviewer", "tester"]


def test_show_prints_prompt_content(capsys):
    expected = load_prompts()["planner"]
    assert main(["show", "planner"]) == 0
    # print() 会在文件内容后追加一个换行符
    assert capsys.readouterr().out == expected + "\n"


def test_validate_returns_zero(capsys):
    assert main(["validate"]) == 0
    assert "校验通过" in capsys.readouterr().out


def test_show_missing_role_returns_error(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_PIPELINE_ROOT", str(tmp_path))
    assert main(["show", "planner"]) == 1
    assert "找不到角色" in capsys.readouterr().err


def test_validate_output_valid_stdin(capsys, monkeypatch):
    payload = json.dumps(
        {"stage": "plan", "agent": "planner", "input": "x", "reason": "r"},
        ensure_ascii=False,
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    assert main(["validate-output", "-"]) == 0
    assert "输出通过校验" in capsys.readouterr().out


def test_validate_output_valid_fenced_stdin(capsys, monkeypatch):
    payload = "```json\n" + json.dumps(
        {"stage": "plan", "agent": "planner", "input": "x", "reason": "r"},
        ensure_ascii=False,
    ) + "\n```"
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    assert main(["validate-output", "-"]) == 0
    assert "输出通过校验" in capsys.readouterr().out


def test_validate_output_invalid_json_returns_error(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{bad"))
    assert main(["validate-output", "-"]) == 1
    assert "JSON 解析失败" in capsys.readouterr().err


def test_validate_output_schema_error_returns_error(capsys, monkeypatch):
    payload = json.dumps(
        {"stage": "plan", "agent": "coder", "input": "x", "reason": "r"},
        ensure_ascii=False,
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    assert main(["validate-output", "-"]) == 1
    assert "agent 应为" in capsys.readouterr().err


def test_validate_output_missing_file_returns_error(capsys, tmp_path):
    assert main(["validate-output", str(tmp_path / "nope.json")]) == 1
    assert "读取输入失败" in capsys.readouterr().err


def test_show_unreadable_prompt_file_returns_error(capsys, monkeypatch, tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "00-orchestrator.md").write_bytes(b"\xba\xba\xba")
    monkeypatch.setenv("AGENT_PIPELINE_ROOT", str(tmp_path))
    assert main(["show", "planner"]) == 1
    assert "读取提示词失败" in capsys.readouterr().err
