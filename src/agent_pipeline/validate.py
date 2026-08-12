"""提示词文件结构校验。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from agent_pipeline.prompts import project_root, prompts_dir, templates_dir

REQUIRED_MARKERS = {
    "00-orchestrator.md": ("System Prompt", "工作流程", "输出 JSON", "阶段说明"),
    "01-planner.md": ("System Prompt", "需求理解", "技术选型", "验收标准", "待确认问题"),
    "02-coder.md": ("System Prompt", '"path"', '"code"', '"notes"'),
    "03-reviewer.md": ("System Prompt", '"verdict"', '"issues"', '"summary"'),
    "04-tester.md": ("System Prompt", '"run_command"', '"coverage_note"'),
}

FENCE = "```"


def extract_json_blocks(text: str) -> list[str]:
    """提取文本中所有 ```json 代码块。"""
    pattern = re.compile(r"```json\n(.*?)```", flags=re.DOTALL)
    return [block.strip() for block in pattern.findall(text)]


def validate_suite(root: Path | None = None) -> list[str]:
    """返回校验错误列表，空列表表示通过。"""
    errors: list[str] = []
    root = root or project_root()
    files = sorted(prompts_dir(root).glob("*.md"))

    for name in set(REQUIRED_MARKERS) - {file.name for file in files}:
        errors.append(f"缺少提示词文件: {name}")

    for path in files:
        text = path.read_text(encoding="utf-8")
        if text.count(FENCE) % 2 != 0:
            errors.append(f"{path.name}: 代码围栏不配对")
        for marker in REQUIRED_MARKERS.get(path.name, ()):
            if marker not in text:
                errors.append(f"{path.name}: 缺少内容「{marker}」")
        for block in extract_json_blocks(text):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}: JSON 无法解析（{exc.msg}）")

    for path in sorted(templates_dir(root).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "{{" not in text or "}}" not in text:
            errors.append(f"{path.name}: 模板缺少占位符")

    return errors


def is_valid(root: Path | None = None) -> bool:
    return not validate_suite(root)
