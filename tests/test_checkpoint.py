"""Checkpoint 存储测试。"""

from agent_pipeline.checkpoint import CheckpointStore


def test_checkpoint_save_load_delete(tmp_path):
    store = CheckpointStore(tmp_path)
    store.save("run-1", {"stage": "code", "n": 1})
    loaded = store.load("run-1")
    assert loaded == {"stage": "code", "n": 1}
    assert store.list_runs() == ["run-1"]
    store.delete("run-1")
    assert store.load("run-1") is None


def test_checkpoint_missing_returns_none(tmp_path):
    store = CheckpointStore(tmp_path)
    assert store.load("missing") is None
