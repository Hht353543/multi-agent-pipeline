# 示例：统计 CSV 每列缺失值

以“Python 脚本读取 CSV 并统计每列缺失值”为例，展示完整调用链路。

## 用户需求

```text
帮我写一个 Python 脚本，读取 CSV 并统计每列缺失值。
```

## 调用链路

```text
用户需求
→ Planner：输出开发计划
→ Coder：按计划生成 main.py
→ Reviewer：审查并给出 verdict
→ 若 needs_fix：Coder 按意见修改 → Reviewer 复审
→ Tester：生成 test_main.py
→ 总控：汇总交付
```

## 各阶段输出示例（节选）

### Planner 输出

```markdown
1. 需求理解：读取指定 CSV 文件，识别表头列，统计每列缺失值（空字符串或 None）数量并输出；
2. 技术选型：Python 3 + 标准库 csv，不引入第三方依赖；
3. 模块划分：main.py 单模块，包含入口与统计函数；
4. 核心流程：解析命令行参数 → 读取 CSV → 按列统计缺失 → 打印结果；
5. 接口设计：count_missing_values(path: str, encoding: str = "utf-8") -> dict[str, int]；
6. 风险与难点：文件不存在、编码错误、空文件、无表头；
7. 验收标准：有表头 CSV 能输出每列缺失数；文件不存在时给出友好错误；空文件返回空字典；
8. 待确认问题：缺失值是否包含 "NULL" / "NA" 等文本标记。
```

### Coder 输出

```python
import csv
import sys


def count_missing_values(csv_path: str, encoding: str = "utf-8") -> dict[str, int]:
    """统计 CSV 每列缺失值（空字符串或 None）数量。"""
    with open(csv_path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return {}
        missing = {col: 0 for col in reader.fieldnames}
        for row in reader:
            for col in reader.fieldnames:
                if row.get(col) in (None, ""):
                    missing[col] += 1
    return missing


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python main.py <csv路径> [编码]")
        sys.exit(1)
    result = count_missing_values(sys.argv[1])
    for col, count in result.items():
        print(f"{col}: {count}")
```

### Reviewer 输出

```json
{
  "verdict": "pass",
  "issues": [
    {
      "severity": "minor",
      "file": "main.py",
      "location": "main()",
      "problem": "未捕获文件不存在 / 编码错误异常",
      "suggestion": "用 try/except 包裹文件读取并输出友好提示"
    }
  ],
  "summary": "功能与验收标准一致，结构清晰，命名规范；建议补充异常提示。"
}
```

### Tester 输出

```python
import pytest

from main import count_missing_values


def test_normal_case(tmp_path):
    """正常路径：统计各列缺失值数量。"""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("a,b,c\n1,,3\n,2,\n", encoding="utf-8")
    assert count_missing_values(str(csv_file)) == {"a": 1, "b": 1, "c": 1}


def test_empty_file(tmp_path):
    """边界条件：空文件返回空字典。"""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")
    assert count_missing_values(str(csv_file)) == {}
```

运行命令：`pytest tests/ -v`

## 总控汇总交付

| 交付项 | 内容 |
| ------ | ---- |
| 开发计划 | 见 Planner 输出 |
| 代码文件清单 | `main.py` |
| 审查结论 | pass（1 个 minor 建议） |
| 测试清单 | `tests/test_main.py`（正常路径 / 空文件） |
