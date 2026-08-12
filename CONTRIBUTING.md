# 参与贡献

## 环境准备

要求 Python 3.9 及以上。安装开发依赖：

```bash
python -m pip install -e ".[dev]"
```

## 常用命令

```bash
pytest                        # 运行测试
agent-pipeline validate       # 校验提示词文件结构
agent-pipeline list           # 列出角色
agent-pipeline show planner   # 查看某个角色的系统提示词
```

## 修改提示词

1. 修改 `prompts/` 下对应角色的 Markdown 文件；
2. 如果输入格式变化，同步更新 `templates/` 中的模板；
3. 运行 `agent-pipeline validate` 与 `pytest`，确保校验通过；
4. 更新 `CHANGELOG.md`。

## 新增角色

1. 在 `prompts/` 中按编号添加文件，如 `05-xxx.md`；
2. 在 `src/agent_pipeline/prompts.py` 的 `ROLES` 和 `src/agent_pipeline/validate.py` 的 `REQUIRED_MARKERS` 中登记；
3. 更新总控提示词中的调度枚举与 `docs/architecture.md` 的说明。

## 提交信息

遵循常规提交规范，使用 `feat`、`fix`、`docs`、`test`、`ci` 等前缀。
