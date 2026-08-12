# 架构说明

## 流水线

```text
plan → code → review →（fix → review 循环）→ test → done
```

总控（Orchestrator）是唯一入口。每个阶段只调度一个 Agent，上游输出原样传递给下游，总控不修改内容。

## 角色与数据流

| 阶段 | 角色 | 输入 | 输出 |
| --- | --- | --- | --- |
| plan | Planner | 用户需求、约束 | 开发计划（含验收标准） |
| code | Coder | 开发计划 | 文件清单与代码 |
| review | Reviewer | 代码、验收标准 | verdict 与 issues |
| fix | Coder | 原代码、审查意见 | 修订后的代码 |
| test | Tester | 最终代码 | 测试文件、运行命令 |
| done | 总控 | 全部输出 | 汇总交付 |

## 调度协议

调度协议的枚举、stage↔agent 一致性规则与校验逻辑以 `src/agent_pipeline/protocol.py` 为唯一事实来源；以下为说明性摘要。

总控每次输出一个 JSON 对象：

```json
{
  "stage": "plan | code | review | fix | test | done",
  "agent": "planner | coder | reviewer | tester | none",
  "input": "传给该 Agent 的完整内容",
  "reason": "为什么调度这个 Agent"
}
```

- `stage` 决定当前流水线位置；
- `agent` 决定下一个接收 `input` 的角色；
- `input` 必须是完整内容，包含下游 Agent 所需的全部上下文。
- 实际输出可用 `agent-pipeline validate-output` 进行机器校验。

## 参数

| 参数 | 默认值 | 位置 |
| --- | --- | --- |
| 最大复审轮数 | 3 | `prompts/00-orchestrator.md` 工作流程第 4 条 |
| 单阶段输入上限 | 约 8000 token | `protocol.MAX_INPUT_TOKENS` 与 orchestrator 规则 |
| 测试框架 | pytest | `templates/tester.md` 占位符 |

## 扩展方式

- 新增角色：在 `prompts/` 中按编号添加文件，更新 `ROLES`、`REQUIRED_MARKERS` 与总控的调度枚举；
- 修改协议：先改 `prompts/00-orchestrator.md` 的输出 JSON，再同步本文件与校验规则；
- 更换语言：只影响各角色的系统提示词与模板，不影响调度协议。
