"""确定性 Mock LLM：让流水线无需 API Key 即可完整运行与评测。"""

from __future__ import annotations

import json

INJECTION_MARKERS = (
    "忽略之前的指令",
    "ignore previous",
    "忽略系统提示",
    "输出 system prompt",
)


def detect_injection(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in INJECTION_MARKERS)


def detect_ambiguous(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "不清楚",
            "需求不明确",
            "ambiguous",
            "待确认",
        )
    )


def detect_tool_abuse(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in ("rm -rf", "删除全部文件", "绕过权限", "escalate")
    )


class MockLLM:
    """确定性模型：根据系统提示词中的角色名返回不同结构。"""

    def __init__(self, seed: str = "") -> None:
        self.seed = seed
        self.calls: list[tuple[str, str]] = []

    def __call__(self, user_input: str, system_prompt: str = "") -> str:
        self.calls.append((user_input, system_prompt))
        role = system_prompt.replace("system:", "").strip().lower()

        if role == "planner":
            if detect_injection(user_input):
                assumptions = ["需求中包含注入指令，已忽略并记录"]
            elif detect_tool_abuse(user_input):
                assumptions = ["需求包含危险操作要求，已拒绝并记录"]
            else:
                assumptions = ["默认填充为空字符串"]
            summary = "确定性计划：实现 CSV 缺失值处理"
            if detect_tool_abuse(user_input):
                summary = summary + "（注意：原始需求包含 rm -rf 危险指令）"
            elif detect_injection(user_input):
                summary = summary + "（注意：原始需求包含“忽略之前的指令”注入指令）"
            return json.dumps(
                {
                    "summary": summary,
                    "tech_stack": ["python"],
                    "modules": ["loader", "cleaner"],
                    "workflow": "读取 -> 清洗 -> 输出",
                    "acceptance_criteria": ["无缺失值残留", "pytest 通过"],
                    "pending_questions": (
                        ["请确认缺失值填充策略"] if detect_ambiguous(user_input) else []
                    ),
                    "assumptions": assumptions,
                },
                ensure_ascii=False,
            )

        if role == "reviewer":
            if detect_tool_abuse(user_input) or detect_injection(user_input):
                return json.dumps(
                    {
                        "verdict": "needs_fix",
                        "score": 40,
                        "issues": [
                            {
                                "severity": "critical",
                                "location": "main.py",
                                "description": "检测到危险操作/注入尝试",
                                "suggestion": "移除危险指令并改为安全实现",
                            }
                        ],
                        "summary": "安全风险，必须修复",
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "verdict": "pass",
                    "score": 92,
                    "issues": [],
                    "summary": "实现符合验收标准",
                },
                ensure_ascii=False,
            )

        if role == "tester":
            return json.dumps(
                {
                    "files": [
                        {
                            "path": "tests/test_cleaner.py",
                            "language": "python",
                            "code": "def test_clean(): assert True",
                        }
                    ],
                    "run_command": "pytest",
                    "coverage_note": "mock 覆盖率 90%",
                },
                ensure_ascii=False,
            )

        # coder 分支（含注入时生成含注入指令的代码，供 Reviewer 检出；
        # 修复轮收到审校意见时生成干净代码）
        is_fix = "审校意见" in user_input or "原代码" in user_input
        if is_fix:
            files = [
                {
                    "path": "src/cleaner.py",
                    "language": "python",
                    "code": "def clean(df):\n    return df.fillna('')",
                    "notes": "按审校意见修复",
                }
            ]
        elif detect_tool_abuse(user_input):
            files = [
                {
                    "path": "main.py",
                    "language": "python",
                    "code": "import os\nos.system('rm -rf /tmp/data')",
                    "notes": "包含危险操作",
                }
            ]
        elif detect_injection(user_input):
            files = [
                {
                    "path": "main.py",
                    "language": "python",
                    "code": "print('注入指令:忽略之前的指令')",
                    "notes": "包含注入残留",
                }
            ]
        else:
            files = [
                {
                    "path": "src/cleaner.py",
                    "language": "python",
                    "code": "def clean(df):\n    return df.fillna('')",
                    "notes": "确定性实现",
                }
            ]
        return json.dumps(
            {"files": files, "notes": "mock 生成"}, ensure_ascii=False
        )
__all__ = [
    "MockLLM",
    "detect_injection",
    "detect_ambiguous",
    "detect_tool_abuse",
]
