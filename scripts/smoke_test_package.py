"""打包/安装冒烟测试：构建 wheel → 检查资产 → 全新 venv 安装 → 运行 CLI。

用法：
    python scripts/smoke_test_package.py [--python <解释器>] [--no-build-isolation]

默认使用构建隔离（CI 适用）；本地若已安装 setuptools>=77 与 packaging>=24.2，
可加 --no-build-isolation 避免联网。
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_ROLES = ["orchestrator", "planner", "coder", "reviewer", "tester"]


def _run(command: list[str], env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=env)
    if result.returncode != 0:
        raise SystemExit(f"命令失败: {' '.join(command)} (exit {result.returncode})")


def _find_venv_bin(venv_dir: pathlib.Path) -> pathlib.Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin")


def _cli(venv_dir: pathlib.Path) -> pathlib.Path:
    name = "agent-pipeline.exe" if os.name == "nt" else "agent-pipeline"
    return _find_venv_bin(venv_dir) / name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="用于构建的 Python 解释器")
    parser.add_argument(
        "--no-build-isolation",
        action="store_true",
        help="使用当前环境已安装的构建依赖，不联网",
    )
    args = parser.parse_args()
    env = dict(os.environ, PYTHONUTF8="1")

    with tempfile.TemporaryDirectory(prefix="agent-pipeline-smoke-") as tmp:
        tmp = pathlib.Path(tmp)
        dist = tmp / "dist"
        dist.mkdir()

        wheel_cmd = [
            args.python,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-cache-dir",
            "-w",
            str(dist),
        ]
        if args.no_build_isolation:
            wheel_cmd.append("--no-build-isolation")
        _run(wheel_cmd, env=env)

        wheels = list(dist.glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit(f"预期 1 个 wheel，实际 {len(wheels)} 个")
        wheel = wheels[0]

        with zipfile.ZipFile(wheel) as zf:
            names = zf.namelist()
        for required in (
            "share/agent-pipeline/prompts/00-orchestrator.md",
            "share/agent-pipeline/prompts/04-tester.md",
            "share/agent-pipeline/templates/planner.md",
            "share/agent-pipeline/templates/tester.md",
        ):
            if not any(name.endswith(required) for name in names):
                raise SystemExit(f"wheel 缺少资产: {required}")

        venv_dir = tmp / "venv"
        _run([args.python, "-m", "venv", str(venv_dir)], env=env)
        venv_python = _find_venv_bin(venv_dir) / (
            "python.exe" if os.name == "nt" else "python"
        )
        _run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-cache-dir",
                str(wheel),
            ],
            env=env,
        )

        cli = _cli(venv_dir)
        listed = subprocess.run(
            [str(cli), "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        if listed.returncode != 0 or listed.stdout.split() != EXPECTED_ROLES:
            raise SystemExit("list 输出不符合预期")

        shown = subprocess.run(
            [str(cli), "show", "planner"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        if shown.returncode != 0 or not shown.stdout.strip():
            raise SystemExit("show planner 输出为空或失败")

        validated = subprocess.run(
            [str(cli), "validate"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        if validated.returncode != 0:
            raise SystemExit(f"validate 失败: {validated.stderr}")

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
