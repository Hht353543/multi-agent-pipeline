# 行为基线（Behavior Baseline）

> 用途：升级计划 TASK-001 的产出，记录升级前项目的可验证行为，作为后续所有任务“保持功能不变”的对照基准。
> 采集日期：2026-08-13

## 0. 仓库与环境状态

- 仓库：`multi-agent-pipeline`
- 当前提交：`030d7e74c391bb253e61580739628df3571ed35b`（Initial commit: multi-agent pipeline prompts and validation tool）
- 跟踪文件数：29
- 工作区状态：干净（`git status --short` 无输出）
- 安装方式：editable（`pip install -e .`），安装位置 `C:\Users\22394\AppData\Local\Programs\Python\Python312\Lib\site-packages`
- 运行环境：Windows / Python 3.12.2 / setuptools 81.0.0 / packaging 23.2 / pip 26.1.2

## 1. CLI 行为

| 命令 | 输出 | 退出码 |
| --- | --- | --- |
| `python -m agent_pipeline --version` | `agent-pipeline 0.1.0` | 0 |
| `python -m agent_pipeline list` | `orchestrator`、`planner`、`coder`、`reviewer`、`tester`（每行一个，按此顺序） | 0 |
| `python -m agent_pipeline validate` | `校验通过` | 0 |
| `python -m agent_pipeline show <role>` | 打印 `prompts/` 下对应角色的 Markdown 文件内容 | 0 |
| `python -m agent_pipeline validate-output <file\|->` | 校验通过输出 `输出通过校验`；失败输出 error 到 stderr | 0 / 1 |

说明：

- `list` 输出顺序即 `ROLES` 顺序。
- `show planner` 输出与 `prompts/01-planner.md` 文件内容一致；其余角色同理。
- 控制台编码注记：本机 Windows 终端为非 UTF-8 代码页时，CLI 输出的中文在部分终端会显示为乱码（例如 `校验通过`），但程序输出与文件内容本身正确，所有文本文件均为无 BOM 的 UTF-8。该现象属于终端环境显示问题，不作为项目缺陷记录；后续可考虑在 README 中提示使用 `PYTHONUTF8=1`。

## 2. 测试基线

命令：`python -m pytest -q`

初始结果：`6 passed in 0.09s`，退出码 0。

升级完成后的结果：`36 passed`，退出码 0；覆盖率 85.49%（≥ 80% 门禁）。

用例清单（6 个）：

- `tests/test_prompts.py::test_roles_are_expected`
- `tests/test_prompts.py::test_prompt_files_are_ordered_and_complete`
- `tests/test_prompts.py::test_load_prompts_returns_all_roles`
- `tests/test_validate.py::test_suite_is_valid`
- `tests/test_validate.py::test_json_blocks_are_parseable`
- `tests/test_validate.py::test_templates_contain_placeholders`

## 3. 角色与调度协议契约

- 角色集合（`ROLES`，顺序固定）：`orchestrator`、`planner`、`coder`、`reviewer`、`tester`
- 提示词文件（按编号排序，必须齐全）：
  - `prompts/00-orchestrator.md`
  - `prompts/01-planner.md`
  - `prompts/02-coder.md`
  - `prompts/03-reviewer.md`
  - `prompts/04-tester.md`
- Orchestrator 调度 JSON（当前以提示词散文与示例定义，无机器可读 Schema）：
  - `stage` ∈ `plan | code | review | fix | test | done`
  - `agent` ∈ `planner | coder | reviewer | tester | none`
  - `input`：传给该 Agent 的完整内容
  - `reason`：为什么调度该 Agent
  - `fix_context`：可选字段（fix 阶段携带 issues 与相关文件，TASK-016 新增）
- fix 复审上限：3 轮（仅 `prompts/00-orchestrator.md` 第 13 行散文约定，代码无强制）
- 升级后：上限由 `protocol.MAX_REVIEW_ROUNDS = 3` 表达，runner 强制执行；单阶段输入上限 `protocol.MAX_INPUT_TOKENS = 8000`；协议校验由 `protocol.validate_dispatch_output()` 与 `validate-output` 子命令提供
- 提示词版本元数据：5 个提示词文件头部 `prompt-version: 0.1.0`
- Reviewer `verdict` ∈ `pass | needs_fix`；critical/major 未解决时必须为 `needs_fix`
- Coder 输出 JSON：`{"files": [{"path", "language", "code"}], "notes"}`
- Tester 输出 JSON：`{"files": [...], "run_command", "coverage_note"}`

## 4. 模板占位符

- `templates/planner.md`：`{{需求描述}}`、`{{技术栈 / 时间 / 其他限制，可留空}}`
- `templates/coder.md`：`{{Planner 的输出}}`
- `templates/reviewer.md`：`{{Coder 输出的 files 代码}}`、`{{Planner 输出的验收标准}}`
- `templates/tester.md`：`{{最终代码}}`、`{{pytest 等}}`

## 5. 校验规则（`validate_suite` 当前行为）

- 检查 5 个必需提示词文件是否存在；
- 每个提示词文件代码围栏数量必须为偶数（`FENCE = "```"`）；
- 按 `REQUIRED_MARKERS` 逐文件检查必需字符串；
- ` ```json ` 代码块必须能被 `json.loads` 解析；
- 每个模板文件必须同时包含 `{{` 与 `}}`；
- 返回错误列表，空列表表示通过；`is_valid()` 为封装函数，当前无调用者。

## 6. 路径解析与环境变量

- `AGENT_PIPELINE_ROOT` 可覆盖仓库根目录（`src/agent_pipeline/prompts.py` 第 13-16 行）；
- 未设置时，`project_root()` 返回 `Path(__file__).resolve().parents[2]`（第 16 行），仅适用于 editable / 源码目录布局；
- `load_prompts()` 从 `prompts/*.md` 读取，角色名由文件名 `NN-role.md` 推导（`split("-", 1)[1]`）。

## 7. 已知问题基线（供后续任务修复后对照）

以下问题在升级前已确认存在，后续任务应分别修复并在本文件追加变更记录：

- P0-1（已修复，TASK-002）：本机执行 `pip wheel . --no-deps --no-build-isolation` 在元数据阶段失败，报 `ImportError: Cannot import packaging.licenses`（setuptools 81.0.0 + packaging 23.2，PEP 639 许可证规范化失败；2026-08-12 实测）。
- P0-2（已修复，TASK-003）：绕过上述问题构建出的 wheel 不含 `prompts/` 与 `templates/`；在全新 venv 中安装后，`show planner` 抛 `KeyError: 'planner'`，`validate` 报告 5 个提示词文件全部缺失（2026-08-12 实测）。
- P1-1（已修复，TASK-009）：`prompts/` 下出现不带 `-` 的 `.md` 文件时，`load_prompts()` 抛 `IndexError`（2026-08-12 实测）。
- P1-2（已修复，TASK-004）：`validate_suite()` 遇到非 UTF-8 `.md` 文件时抛 `UnicodeDecodeError`，而非返回错误列表（2026-08-12 实测）。
- P1-3（已修复，TASK-005）：`prompts/04-tester.md` 第 13 行的系统提示词内含模板占位符 `{{测试框架，如 pytest}}`，与模板职责混用。
- P2（已修复，TASK-010/011/024）：`src/agent_pipeline/cli.py` 第 52 行 `return 2` 不可达（已移除）；`src/agent_pipeline/validate.py` 的 `is_valid` 保留为公开 API 并补测试；版本号改为单一来源（`importlib.metadata`，`__init__.py` 仅保留兜底常量）。

## 8. 变更记录

| 日期 | 任务 | 行为变化 | 验证结果 |
| --- | --- | --- | --- |
| 2026-08-13 | TASK-001 | 无（仅新增本基线文档） | 文档内容与实测 CLI、测试输出一致 |
| 2026-08-13 | TASK-002 | 构建依赖增加 `packaging>=24.2` | 隔离环境 `pip wheel .` 成功 |
| 2026-08-13 | TASK-003 | wheel 包含 prompts/templates；资源定位增加已安装数据目录回退 | 全新 venv 安装后 list/show/validate 正常；pytest 通过 |
| 2026-08-13 | TASK-004 | CLI/校验器异常路径输出友好错误；统一 `_print_error` | 4 类异常场景均返回非零退出码且无 traceback |
| 2026-08-13 | TASK-005 | Tester 系统提示词不再包含模板占位符 | validate 与 pytest 通过 |
| 2026-08-13 | TASK-006 | 模板与 Orchestrator 增加数据边界与注入防护规则 | validate 与 pytest 通过 |
| 2026-08-13 | TASK-007 | Coder/Tester 增加 path 与 run_command 安全约束；集成文档增加平台要求 | validate 与 pytest 通过 |
| 2026-08-13 | TASK-008 | 新增 `protocol.py` 单一事实来源 | 公开 API 不变；pytest 通过 |
| 2026-08-13 | TASK-009 | `load_prompts` 对未登记文件抛 `ValueError` | 边界测试通过 |
| 2026-08-13 | TASK-010 | 版本号改用 `importlib.metadata` 单一来源 | `--version` 输出不变 |
| 2026-08-13 | TASK-011 | 移除不可达 `return 2`；`is_valid` 保留 | pytest 通过 |
| 2026-08-13 | TASK-012 | 新增 `validate_dispatch_output` 与 stage↔agent 一致性校验 | 合法/非法样例通过 |
| 2026-08-13 | TASK-013 | 新增 `validate-output` 子命令（文件/stdin，支持围栏） | 6 类输入场景通过 |
| 2026-08-13 | TASK-014 | 文档改为引用协议唯一来源；README/integration 补充命令 | validate 与 pytest 通过 |
| 2026-08-13 | TASK-015 | 新增 `runner.py` 轻量执行器（注入 call_llm，重试一次，fix 上限） | 4 类 fake-provider 场景通过 |
| 2026-08-13 | TASK-016 | fix 上下文瘦身规则；协议新增可选 `fix_context` | 校验与测试通过 |
| 2026-08-13 | TASK-017 | 新增 `MAX_INPUT_TOKENS=8000` 与超限规则 | 常量与提示词同步 |
| 2026-08-13 | TASK-018 | 集成文档增加缓存/去重指引 | 文档评审 |
| 2026-08-13 | TASK-019 | 四个 JSON 角色增加输出严格性规则（Planner 不适用） | validate 与 pytest 通过 |
| 2026-08-13 | TASK-020 | 错误恢复协议与 runner 重试一次；fix 超限转人工 | 重试/失败场景通过 |
| 2026-08-13 | TASK-021 | Coder/Reviewer 增加敏感信息硬编码约束 | validate 与 pytest 通过 |
| 2026-08-13 | TASK-022 | 提示词增加 `prompt-version`；新增 golden 评测集与评测文档 | JSON 可解析、版本头齐全 |
| 2026-08-13 | TASK-023 | 新增 RAG 决策文档（当前不引入） | 文档评审 |
| 2026-08-13 | TASK-024 | 校验器失败路径与边界单元测试（fixture 化） | 27 项测试通过 |
| 2026-08-13 | TASK-025 | CLI 集成测试（list/show/validate/validate-output/错误路径） | 36 项测试通过 |
| 2026-08-13 | TASK-026 | 新增打包冒烟脚本与 CI job | 本地冒烟通过（SMOKE TEST PASSED） |
| 2026-08-13 | TASK-027 | 接入 ruff/mypy/pytest-cov 与覆盖率门禁 | ruff、mypy 通过；覆盖率 85.49% |
| 2026-08-13 | TASK-028 | CI 增加 Windows 矩阵、pip 缓存与 lint/type 步骤 | YAML 校验通过（CI 推送后生效） |
| 2026-08-13 | TASK-029 | 统一 CLI 错误输出（随 TASK-004 落地） | 错误输出全部经 `_print_error` |

## 9. 维护说明

- 本文件是升级过程的对照快照，不是功能文档；
- 后续任何任务若改变第 1-7 节中的行为，必须在“变更记录”中登记，并注明验证结果；
- 若契约发生重大变更，应先更新本基线，再更新 `docs/architecture.md` 与相关提示词。
