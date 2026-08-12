# 集成说明

## 多 Agent 平台

以 Dify、Coze 或自研多 Agent 框架为例：

1. 将 `prompts/` 下 5 个文件分别配置为各 Agent 的系统提示词；
2. 总控 Agent 接收用户需求，输出调度 JSON；
3. 平台按 `agent` 字段把 `input` 转发给对应 Agent，并将返回结果交回总控；
4. `stage == "done"` 时停止，由总控汇总交付。

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
```

## 环境变量

`AGENT_PIPELINE_ROOT` 可指定仓库根目录；未设置时按包所在位置自动探测。
