"""提示词文件的定位与读取。"""

from __future__ import annotations

import os
from pathlib import Path

ROLES = ("orchestrator", "planner", "coder", "reviewer", "tester")


def project_root() -> Path:
    """返回仓库根目录，可用环境变量 AGENT_PIPELINE_ROOT 覆盖。"""
    env_root = os.environ.get("AGENT_PIPELINE_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def prompts_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "prompts"


def templates_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "templates"


def load_prompts(root: Path | None = None) -> dict[str, str]:
    """读取全部角色提示词，返回 {角色名: 内容}。"""
    result: dict[str, str] = {}
    for path in sorted(prompts_dir(root).glob("*.md")):
        role = path.stem.split("-", 1)[1]
        result[role] = path.read_text(encoding="utf-8")
    return result
