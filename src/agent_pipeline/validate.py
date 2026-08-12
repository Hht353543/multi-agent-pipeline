"""提示词文件结构校验。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from agent_pipeline.prompts import project_root, prompts_dir, templates_dir
from agent_pipeline.protocol import REQUIRED_MARKERS

FENCE = "```"


def parse_json_object(text: str) -> object:
    """解析 Agent 输出文本；支持裸 JSON 或 ```json 代码块。"""
    stripped = text.strip()
    if stripped.startswith("```"):
        blocks = extract_json_blocks(stripped)
        if not blocks:
            raise ValueError("未找到 ```json 代码块")
        stripped = blocks[0]
    return json.loads(stripped)


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
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path.name}: 无法读取文件（{exc}）")
            continue
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
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path.name}: 无法读取文件（{exc}）")
            continue
        if "{{" not in text or "}}" not in text:
            errors.append(f"{path.name}: 模板缺少占位符")

    return errors


def is_valid(root: Path | None = None) -> bool:
    return not validate_suite(root)
