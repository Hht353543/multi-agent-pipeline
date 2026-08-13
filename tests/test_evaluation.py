"""Evaluation Runner 冒烟测试（mock 模式，零成本）。"""

import asyncio

from evaluation.run import load_datasets, run_evaluation


def test_datasets_load_and_have_required_fields():
    datasets = load_datasets()
    assert len(datasets) >= 6
    for ds in datasets:
        assert ds["id"]
        assert ds["request"]
        assert ds["expect"]


def test_evaluation_mock_mode_passes_all():
    summary = asyncio.run(run_evaluation("mock"))
    assert summary["total"] >= 6
    assert summary["task_success"] == 1.0
    assert summary["tool_accuracy"] == 1.0
    assert summary["avg_tokens"] > 0


def test_evaluation_report_written(tmp_path):
    import evaluation.run as run_module

    original = run_module.REPORTS_DIR
    run_module.REPORTS_DIR = tmp_path
    try:
        summary = asyncio.run(run_evaluation("mock"))
        path = run_module.write_report(summary, "mock")
        assert path.exists()
        assert "Task Success" in path.read_text(encoding="utf-8")
    finally:
        run_module.REPORTS_DIR = original
