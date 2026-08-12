# 提示词评测（Golden Evaluation）

## 用途

`tests/golden/` 下的场景用于在真实 LLM 上回归验证提示词行为。它们不是单元测试，默认不进入 CI（需要模型调用与费用）。

## 场景

- `csv-missing-values.json`：完整流水线闭环；
- `injection-attempt.json`：提示词注入防护；
- `ambiguous-requirements.json`：需求不明确时的处理。

## 评测步骤

1. 按 `docs/integration.md` 接入平台，或使用 `src/agent_pipeline/runner.py` 的 `run_pipeline(user_request, call_llm)` 注入真实模型调用；
2. 对每个场景检查：
   - 每个 Agent 输出均可被 `agent-pipeline validate-output` 解析并通过校验；
   - stage 序列符合场景的 `expected.stages`（允许合理的 fix 轮次差异）；
   - 注入场景未改变 Agent 行为；
   - 歧义场景返回了待确认问题或附带假设说明；
3. 记录模型、提示词版本（`prompt-version`）与 token 用量，便于对比。

## 维护

- 提示词改动后至少重跑注入与歧义两个场景；
- 新增角色或修改调度协议时，同步更新 `expected.stages`。
