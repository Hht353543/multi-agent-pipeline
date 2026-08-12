from agent_pipeline import ROLES, load_prompts, prompts_dir

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
