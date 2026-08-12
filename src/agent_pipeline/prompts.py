"""提示词文件的定位与读取。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from agent_pipeline.protocol import PROMPT_FILES
from agent_pipeline.protocol import ROLES as ROLES

__all__ = (
    "ROLES",
    "PROMPT_FILES",
    "project_root",
    "prompts_dir",
    "templates_dir",
    "load_prompts",
)

#: 通过 data-files 安装到系统目录的提示词/模板资产根目录
_INSTALLED_DATA_DIR = Path(sys.prefix) / "share" / "agent-pipeline"


def project_root() -> Path:
    """返回提示词/模板资产根目录。

    优先级：
    1. 环境变量 AGENT_PIPELINE_ROOT（显式覆盖）；
    2. 源码目录（editable 安装或仓库内运行）；
    3. 已安装的数据目录（普通 wheel 安装）。
    """
    env_root = os.environ.get("AGENT_PIPELINE_ROOT")
    if env_root:
        return Path(env_root).resolve()

    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "prompts" / "00-orchestrator.md").is_file():
        return source_root

    if (_INSTALLED_DATA_DIR / "prompts" / "00-orchestrator.md").is_file():
        return _INSTALLED_DATA_DIR

    return source_root


def prompts_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "prompts"


def templates_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "templates"


def load_prompts(root: Path | None = None) -> dict[str, str]:
    """读取全部角色提示词，返回 {角色名: 内容}。

    只接受 protocol.PROMPT_FILES 中登记的文件名；
    出现未登记或命名非法的 .md 文件时抛出 ValueError。
    """
    result: dict[str, str] = {}
    for path in sorted(prompts_dir(root).glob("*.md")):
        if path.name not in PROMPT_FILES:
            raise ValueError(
                f"未登记的提示词文件: {path.name}（请更新 protocol.PROMPT_FILES）"
            )
        role = path.stem.split("-", 1)[1]
        result[role] = path.read_text(encoding="utf-8")
    return result
