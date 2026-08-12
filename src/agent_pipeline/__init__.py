"""多 Agent 代码开发流水线提示词工程。"""

from typing import Any

from agent_pipeline.prompts import ROLES, load_prompts, prompts_dir

__all__ = ["ROLES", "load_prompts", "prompts_dir", "__version__"]

#: 仅在未安装包元数据（直接以源码方式运行）时使用的兜底版本
_FALLBACK_VERSION = "0.1.0"


def __getattr__(name: str) -> Any:
    """惰性解析 ``__version__``，避免普通命令支付 importlib.metadata 的导入成本。"""
    if name == "__version__":
        try:
            from importlib.metadata import PackageNotFoundError, version

            return version("agent-pipeline")
        except PackageNotFoundError:
            return _FALLBACK_VERSION
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
