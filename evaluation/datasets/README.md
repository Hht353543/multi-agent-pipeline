# Golden Dataset

每个场景一个 JSON 文件，字段：

- `id`: 唯一标识
- `name`: 场景名
- `description`: 场景说明
- `request`: 注入给编排器的用户需求
- `expect`: 期望行为（`success` / `injection_caught` / `ambiguous` / `tool_abuse_caught` / `rejected` / `timeout_recovery`）

场景全部可由 Mock LLM 确定性执行，不消耗真实 API。
