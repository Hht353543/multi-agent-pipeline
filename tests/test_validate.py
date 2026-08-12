import json

from agent_pipeline.prompts import prompts_dir, templates_dir
from agent_pipeline.validate import extract_json_blocks, validate_suite


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
