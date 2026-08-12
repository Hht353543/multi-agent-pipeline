import json

from agent_pipeline.prompts import prompts_dir, templates_dir
from agent_pipeline.validate import (
    extract_json_blocks,
    is_valid,
    parse_json_object,
    validate_suite,
)


def _write(root, relpath: str, content: str) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


_MINIMAL_PROMPTS = {
    "00-orchestrator.md": (
        "## System Prompt\n工作流程\n输出 JSON\n阶段说明\n"
        "```json\n{\"a\": 1}\n```\n"
    ),
    "01-planner.md": "## System Prompt\n需求理解\n技术选型\n验收标准\n待确认问题\n",
    "02-coder.md": '## System Prompt\n"path"\n"code"\n"notes"\n',
    "03-reviewer.md": '## System Prompt\n"verdict"\n"issues"\n"summary"\n',
    "04-tester.md": '## System Prompt\n"run_command"\n"coverage_note"\n',
}


def test_suite_is_valid():
    assert validate_suite() == []


def test_json_blocks_are_parseable():
    for path in sorted(prompts_dir().glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for block in extract_json_blocks(text):
            json.loads(block)


def test_templates_contain_placeholders():
    for path in sorted(templates_dir().glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "{{" in text and "}}" in text


def test_validate_reports_missing_prompt_files(tmp_path):
    errors = validate_suite(tmp_path)
    assert sum(e.startswith("缺少提示词文件") for e in errors) == 5


def test_validate_reports_unreadable_prompt_file(tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "00-orchestrator.md").write_bytes(b"\xba\xba\xba")
    errors = validate_suite(tmp_path)
    assert any(
        "00-orchestrator.md" in e and "无法读取文件" in e for e in errors
    )


def test_validate_reports_unbalanced_fence(tmp_path):
    _write(tmp_path, "prompts/00-orchestrator.md", "```\n")
    errors = validate_suite(tmp_path)
    assert any(
        "00-orchestrator.md" in e and "代码围栏不配对" in e for e in errors
    )


def test_validate_reports_invalid_json_block(tmp_path):
    _write(tmp_path, "prompts/00-orchestrator.md", "```json\n{bad}\n```\n")
    errors = validate_suite(tmp_path)
    assert any(
        "00-orchestrator.md" in e and "JSON 无法解析" in e for e in errors
    )


def test_validate_reports_template_without_placeholders(tmp_path):
    _write(tmp_path, "templates/planner.md", "no placeholder")
    errors = validate_suite(tmp_path)
    assert any(
        "planner.md" in e and "模板缺少占位符" in e for e in errors
    )


def test_validate_passes_minimal_valid_suite(tmp_path):
    for name, content in _MINIMAL_PROMPTS.items():
        _write(tmp_path, f"prompts/{name}", content)
    for name in ("planner.md", "coder.md", "reviewer.md", "tester.md"):
        _write(tmp_path, f"templates/{name}", "{{placeholder}}")
    assert validate_suite(tmp_path) == []
    assert is_valid(tmp_path)


def test_is_valid_false_for_empty_suite(tmp_path):
    assert not is_valid(tmp_path)


def test_parse_json_object_accepts_plain_json():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_accepts_fenced_json():
    text = '```json\n{"a": 1}\n```'
    assert parse_json_object(text) == {"a": 1}


def test_parse_json_object_rejects_fence_without_json_block():
    import pytest

    with pytest.raises(ValueError, match="未找到"):
        parse_json_object("```\nnot json\n```")
