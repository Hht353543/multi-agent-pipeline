import pytest

import agent_pipeline
from agent_pipeline import ROLES, load_prompts, prompts_dir
from agent_pipeline.prompts import project_root

EXPECTED_FILES = [
    "00-orchestrator",
    "01-planner",
    "02-coder",
    "03-reviewer",
    "04-tester",
]


def test_roles_are_expected():
    assert ROLES == ("orchestrator", "planner", "coder", "reviewer", "tester")


def test_prompt_files_are_ordered_and_complete():
    files = sorted(prompts_dir().glob("*.md"))
    assert [path.stem for path in files] == EXPECTED_FILES


def test_load_prompts_returns_all_roles():
    prompts = load_prompts()
    assert set(prompts) == set(ROLES)
    for content in prompts.values():
        assert content.strip()
        assert "## System Prompt" in content


def test_load_prompts_rejects_unregistered_file(tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "notes.md").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="未登记的提示词文件"):
        load_prompts(tmp_path)


def test_load_prompts_reads_registered_file(tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "00-orchestrator.md").write_text("content", encoding="utf-8")
    assert load_prompts(tmp_path) == {"orchestrator": "content"}


def test_project_root_honors_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_PIPELINE_ROOT", str(tmp_path))
    assert project_root() == tmp_path.resolve()


def test_version_falls_back_without_metadata(monkeypatch):
    from importlib.metadata import PackageNotFoundError

    def raise_not_found(distribution_name):
        raise PackageNotFoundError(distribution_name)

    monkeypatch.setattr("importlib.metadata.version", raise_not_found)
    assert agent_pipeline.__version__ == "0.1.0"
