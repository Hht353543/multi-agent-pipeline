"""显式状态机测试。"""

import pytest

from agent_pipeline.state_machine import StateMachine


def test_normal_flow():
    machine = StateMachine()
    for stage in ("human_approval", "code", "review", "test", "done"):
        machine.transition(stage)
    assert machine.stage == "done"
    assert machine.history == ["plan", "human_approval", "code", "review", "test", "done"]


def test_illegal_transition_raises():
    machine = StateMachine()
    with pytest.raises(ValueError, match="非法状态转移"):
        machine.transition("done")


def test_fix_loop_is_legal():
    machine = StateMachine()
    machine.transition("human_approval")
    machine.transition("code")
    machine.transition("review")
    machine.transition("fix")
    machine.transition("review")
    machine.transition("test")
    machine.transition("done")
    assert machine.stage == "done"


def test_reset():
    machine = StateMachine()
    machine.transition("human_approval")
    machine.reset()
    assert machine.stage == "plan"
