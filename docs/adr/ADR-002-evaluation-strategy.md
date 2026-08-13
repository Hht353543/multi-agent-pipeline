# ADR-002：评测策略

- 状态：Accepted
- 日期：2026-08-13

## Context

Agent 流水线是否有用需要量化：任务成功率、工具准确性、审校检出、延迟、
token 与成本。CI 不能依赖真实 API。

## Decision

建立 `evaluation/`：

- Golden Dataset 覆盖正常流程、注入攻击、歧义需求、工具滥用、人工驳回、
  超时恢复；
- Mock LLM 确定性执行，`EVAL_MODE=mock` 默认零成本；
- 输出 Task Success / Tool Accuracy / Latency / Tokens / Cost 与逐场景报告；
- `EVAL_MODE=real` 可通过 OpenAI 兼容接口切真实模型。

## Alternatives

- 只用单测：无法回答端到端行为；
- 只跑真实 API：成本高、不可复现。

## Consequences

- Prompt 或调度协议变更后必须重跑评测；
- 新增场景先补 Golden Dataset，再改实现。
