# multi-agent-pipeline

面向多 Agent 协作的代码开发流水线提示词工程。仓库包含 5 个角色的系统提示词、可复用的用户输入模板、完整的调用链路示例，以及一个用于校验提示词结构的命令行工具。

## 角色

| 角色 | 提示词文件 | 输入 | 输出 |
| --- | --- | --- | --- |
| 总控 Orchestrator | [prompts/00-orchestrator.md](prompts/00-orchestrator.md) | 用户需求 | 调度指令 JSON |
| 需求分析 Planner | [prompts/01-planner.md](prompts/01-planner.md) | 需求与约束 | 开发计划 |
| 代码生成 Coder | [prompts/02-coder.md](prompts/02-coder.md) | 开发计划 | 文件清单与代码 |
| 代码审查 Reviewer | [prompts/03-reviewer.md](prompts/03-reviewer.md) | 代码与验收标准 | 审查结论 JSON |
| 测试生成 Tester | [prompts/04-tester.md](prompts/04-tester.md) | 最终代码 | 测试文件与运行命令 |

## 流水线

```text
用户需求
  → Orchestrator
      → Planner：输出开发计划
      → Coder：按计划生成代码
      → Reviewer：审查代码
          → needs_fix：Coder 修改 → Reviewer 复审（最多 3 轮）
          → pass：继续
      → Tester：生成单元测试
  → Orchestrator 汇总交付
```

## 目录结构

```text
.
├── prompts/      系统提示词（按调用顺序编号）
├── templates/    用户输入模板（替换占位符后使用）
├── examples/     调用链路与各阶段输出示例
├── docs/         架构与集成说明
├── src/          提示词读取与校验工具
├── tests/        校验工具测试
└── .github/      CI 配置
```

## 使用

### 多 Agent 平台

将 `prompts/` 下的文件分别配置为各 Agent 的系统提示词，总控 Agent 根据输出 JSON 中的 `agent` 与 `input` 调度下一个角色。

### 单会话接力

1. 向总控提出需求，得到调度 JSON；
2. 从 `templates/` 找到对应模板，把 JSON 中的 `input` 填入占位符；
3. 连同该角色的系统提示词一起发送，得到输出后再交给总控进入下一阶段。

### 命令行工具

```bash
python -m pip install -e ".[dev]"

agent-pipeline list          # 列出全部角色
agent-pipeline show planner  # 查看某个角色的系统提示词
agent-pipeline validate      # 校验提示词文件结构
```

## 开发

```bash
python -m pip install -e ".[dev]"
pytest
```

## 文档

- [架构说明](docs/architecture.md)
- [集成说明](docs/integration.md)
- [示例：统计 CSV 每列缺失值](examples/csv-missing-values.md)

## 许可证

[MIT](LICENSE)
