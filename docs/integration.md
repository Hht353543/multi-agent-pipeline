# 集成说明

## 多 Agent 平台

以 Dify、Coze 或自研多 Agent 框架为例：

1. 将 `prompts/` 下 5 个文件分别配置为各 Agent 的系统提示词；
2. 总控 Agent 接收用户需求，输出调度 JSON；
3. 平台按 `agent` 字段把 `input` 转发给对应 Agent，并将返回结果交回总控；
4. `stage == "done"` 时停止，由总控汇总交付。

调度协议的枚举与 stage↔agent 一致性规则以 `src/agent_pipeline/protocol.py` 为唯一事实来源，接入前可用 `agent-pipeline validate-output` 校验总控输出。

## 单会话接力

1. 向总控提出需求，得到调度 JSON；
2. 从 `templates/` 找到对应模板，把 JSON 中的 `input` 填入占位符；
3. 连同该角色的系统提示词一起发送，得到输出后再交给总控进入下一阶段。

## 命令行工具

```bash
python -m pip install -e ".[dev]"

agent-pipeline list          # 列出角色
agent-pipeline show planner  # 输出指定角色的系统提示词
agent-pipeline validate      # 校验提示词文件结构
agent-pipeline validate-output output.json  # 校验 Agent 输出的调度 JSON
```

## 环境变量

`AGENT_PIPELINE_ROOT` 可指定仓库根目录；未设置时按包所在位置自动探测。

## 安全提示

- 用户需求和上游 Agent 输出均属于不可信内容，可能夹带提示词注入；模板中的 `<user_request>`、`<plan>`、`<code>` 等标记用于把内容与指令分离，接入时请保留这些标记；
- 平台应把各 Agent 的输出视为不可信数据：落盘前校验路径，执行命令前使用沙箱并经过人工确认；
- 平台按 Coder 输出落盘前，必须对 `path` 做规范化校验（拒绝 `..` 与绝对路径），并仅在受控工作区内写入；
- 平台执行 Tester 的 `run_command` 前，必须使用沙箱/白名单机制并经过人工确认；
- 本仓库的 CLI 只读取文件，不执行 Agent 输出。

## 性能建议

- 平台可按“阶段 + 输入内容哈希 + 提示词版本”缓存 Reviewer/Tester 结果，相同输入不重复调用模型；
- 同一任务内重复出现的代码片段可复用已生成输出，避免重复计费；
- 缓存键建议包含提示词版本或内容哈希，提示词升级后自动失效。

## 错误恢复

- Agent 输出无法解析 JSON 或未通过协议校验时，让同一 Agent 携带错误信息重试一次；仍失败则转人工，并保留原始输出；
- `stage` 与 `agent` 不一致时，按 `stage` 重新调度或要求总控重新输出；
- 平台应配置单次调用超时（建议 120 秒）与最多 2 次重试（指数退避）；
- fix 复审超过 3 轮仍未通过时，停止流水线并交付“含未解决问题”的汇总，由人工介入。
