"""遥测与 token 估算测试。"""

from agent_pipeline.telemetry import Telemetry, estimate_tokens


def test_estimate_tokens_cjk_and_ascii():
    assert estimate_tokens("中" * 10) == 10
    assert estimate_tokens("abcd") == 1


def test_telemetry_records_llm_and_summary():
    t = Telemetry(run_id="r1")
    step = t.start_step("plan", "planner")
    t.record_llm(step, "输入：你好", "输出：好的", 12.5)
    summary = t.summary()
    assert summary["llm_calls"] == 1
    assert summary["total_tokens"] == step.input_tokens + step.output_tokens
    assert summary["total_duration_ms"] >= 12.0


def test_telemetry_cost_and_error():
    t = Telemetry(run_id="r2", cost_per_1k_input=1.0, cost_per_1k_output=2.0)
    step = t.start_step("code", "coder")
    t.record_llm(step, "a" * 4000, "b" * 4000, 1.0)
    assert step.estimated_cost > 0
    t.fail_step(step, "boom", retries=2)
    summary = t.summary()
    assert summary["errors"] == ["boom"]
    assert summary["retries"] == 2
