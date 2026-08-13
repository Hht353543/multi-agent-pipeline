# ADR-001：自研轻量 Agent 运行时

- 状态：Accepted
- 日期：2026-08-13

## Context

原项目是提示词 + 调度协议校验工具，没有可执行的 Agent 运行时。
为了证明“理解 Agent 原理并能从零设计”，需要把编排器、状态机、工具、
遥测、Checkpoint 落地为可运行代码。

## Decision

实现自研运行时（不引入 LangGraph/LangChain）：

- `BaseAgent` / `AgentContext` / `AgentRegistry`：角色即类，注册即扩展；
- `StateMachine`：显式阶段与合法转移，非法跳转直接报错；
- `ToolRegistry` + 权限矩阵：Agent 只能通过工具访问资源；
- `Telemetry`：run/trace/step 级延迟、token、成本、重试、工具调用；
- `CheckpointStore`：按步骤落盘，失败可从断点续跑；
- `Orchestrator.run()`：同步入口包装异步 Agent，返回结构化 `PipelineResult`。

## Alternatives

- LangGraph：抽象层级高，面试时难以展示底层设计；
- 维持纯提示词工具：无法演示 Agent 决策与恢复。

## Consequences

- 项目从“提示词库”升级为可评估的 Agent 系统；
- 每个新增组件（工具/Agent/阶段）必须配测试与评测场景。
