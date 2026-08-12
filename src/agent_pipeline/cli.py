"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

from agent_pipeline.prompts import ROLES, load_prompts
from agent_pipeline.protocol import validate_dispatch_output
from agent_pipeline.validate import parse_json_object, validate_suite


class _VersionAction(argparse.Action):
    """仅在 --version 触发时解析版本号，避免普通命令加载 importlib.metadata。"""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        from agent_pipeline import __version__

        print(f"{parser.prog} {__version__}")
        parser.exit()


def _print_error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def _read_text(source: str) -> str:
    """读取命令输入：'-' 表示标准输入，否则按 UTF-8 读取文件。"""
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-pipeline",
        description="多 Agent 代码开发流水线提示词工具",
    )
    parser.add_argument(
        "--version",
        action=_VersionAction,
        nargs=0,
        help="显示版本并退出",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list", help="列出全部角色")

    show = subcommands.add_parser("show", help="输出指定角色的系统提示词")
    show.add_argument("role", choices=ROLES)

    subcommands.add_parser("validate", help="校验提示词文件结构")

    validate_output = subcommands.add_parser(
        "validate-output", help="校验 Agent 输出的调度 JSON"
    )
    validate_output.add_argument(
        "file", nargs="?", default="-", help="JSON 文件路径，或 - 读取标准输入"
    )
    return parser


def _command_list(args: argparse.Namespace) -> int:
    for role in ROLES:
        print(role)
    return 0


def _command_show(args: argparse.Namespace) -> int:
    try:
        prompts = load_prompts()
        print(prompts[args.role])
    except KeyError:
        _print_error(
            f"找不到角色「{args.role}」的提示词，请检查安装或 AGENT_PIPELINE_ROOT"
        )
        return 1
    except (OSError, UnicodeDecodeError) as exc:
        _print_error(f"读取提示词失败: {exc}")
        return 1
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    try:
        errors = validate_suite()
    except (OSError, UnicodeDecodeError) as exc:
        _print_error(f"校验失败: {exc}")
        return 1
    if errors:
        for error in errors:
            _print_error(error)
        return 1
    print("校验通过")
    return 0


def _command_validate_output(args: argparse.Namespace) -> int:
    try:
        text = _read_text(args.file)
    except (OSError, UnicodeDecodeError) as exc:
        _print_error(f"读取输入失败: {exc}")
        return 1
    try:
        obj = parse_json_object(text)
    except ValueError as exc:
        _print_error(f"JSON 解析失败: {exc}")
        return 1
    errors = validate_dispatch_output(obj)
    if errors:
        for error in errors:
            _print_error(error)
        return 1
    print("输出通过校验")
    return 0


COMMAND_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "list": _command_list,
    "show": _command_show,
    "validate": _command_validate,
    "validate-output": _command_validate_output,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = COMMAND_HANDLERS.get(args.command)
    if handler is None:
        raise AssertionError(f"未处理的命令: {args.command}")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
