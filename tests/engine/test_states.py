"""Tests for hantek_dso2d15.engine.states — Task E1."""

import pytest
from hantek_dso2d15.engine.states import RunState


def test_members_count():
    """RunState должен иметь ровно 3 члена."""
    assert len(RunState) == 3


def test_string_values():
    """Все значения RunState должны быть строками."""
    for member in RunState:
        assert isinstance(member.value, str), (
            f"{member.name}.value должно быть str, получено {type(member.value)}"
        )


def test_stopped_value():
    assert RunState.STOPPED.value == "stopped"


def test_running_value():
    assert RunState.RUNNING.value == "running"


def test_single_value():
    assert RunState.SINGLE.value == "single"


def test_lookup_by_value_running():
    """RunState('running') is RunState.RUNNING."""
    assert RunState("running") is RunState.RUNNING


def test_lookup_by_value_stopped():
    assert RunState("stopped") is RunState.STOPPED


def test_lookup_by_value_single():
    assert RunState("single") is RunState.SINGLE


def test_invalid_value_raises():
    with pytest.raises(ValueError):
        RunState("unknown")
