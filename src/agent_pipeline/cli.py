"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from agent_pipeline import __version__
from agent_pipeline.prompts import ROLES, load_prompts
from agent_pipeline.validate import validate_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-pipeline",
        description="多 Agent 代码开发流水线提示词工具",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list", help="列出全部角色")

    show = subcommands.add_parser("show", help="输出指定角色的系统提示词")
    show.add_argument("role", choices=ROLES)

    subcommands.add_parser("validate", help="校验提示词文件结构")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "list":
        for role in ROLES:
            print(role)
        return 0

    if args.command == "show":
        prompts = load_prompts()
        print(prompts[args.role])
        return 0

    if args.command == "validate":
        errors = validate_suite()
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        print("校验通过")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
