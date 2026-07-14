import pytest

from rescuemind.execution import MissionExecutor, MissionTask, TaskState


def assign_and_start(task: MissionTask) -> None:
    MissionExecutor.transition(task, TaskState.ASSIGNED, 1.0, "allocated", "uav-1")
    MissionExecutor.transition(task, TaskState.IN_PROGRESS, 2.0, "started", "uav-1")


def test_successful_task_lifecycle_is_auditable() -> None:
    task = MissionTask("inspect-h1")
    assign_and_start(task)
    event = MissionExecutor.transition(task, TaskState.SUCCEEDED, 3.0, "verified")
    assert task.state == TaskState.SUCCEEDED
    assert task.attempt == 1
    assert len(task.history) == 3
    assert event.reason == "verified"


def test_recoverable_failure_requests_retry() -> None:
    task = MissionTask("inspect-h1", max_attempts=2)
    assign_and_start(task)
    event = MissionExecutor.report_failure(task, 3.0, "temporary sensor dropout", True)
    assert event.new_state == TaskState.RETRY_PENDING
    assert task.assigned_agent_id is None


def test_agent_failure_requests_reassignment() -> None:
    task = MissionTask("inspect-h1")
    assign_and_start(task)
    event = MissionExecutor.report_failure(task, 3.0, "agent offline", True, agent_failed=True)
    assert event.new_state == TaskState.REASSIGNMENT_REQUIRED


def test_exhausted_attempts_fail_terminally() -> None:
    task = MissionTask("inspect-h1", max_attempts=1)
    assign_and_start(task)
    event = MissionExecutor.report_failure(task, 3.0, "persistent fault", True)
    assert event.new_state == TaskState.FAILED


def test_assignment_requires_agent() -> None:
    with pytest.raises(ValueError, match="agent_id"):
        MissionExecutor.transition(MissionTask("t"), TaskState.ASSIGNED, 1.0, "allocated")


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid transition"):
        MissionExecutor.transition(MissionTask("t"), TaskState.SUCCEEDED, 1.0, "skip")


def test_updates_must_be_monotonic() -> None:
    task = MissionTask("t")
    MissionExecutor.transition(task, TaskState.ASSIGNED, 2.0, "allocated", "uav-1")
    with pytest.raises(ValueError, match="monotonic"):
        MissionExecutor.transition(task, TaskState.IN_PROGRESS, 1.0, "late")


def test_terminal_state_cannot_restart() -> None:
    task = MissionTask("t")
    assign_and_start(task)
    MissionExecutor.transition(task, TaskState.SUCCEEDED, 3.0, "done")
    with pytest.raises(ValueError, match="invalid transition"):
        MissionExecutor.transition(task, TaskState.ASSIGNED, 4.0, "restart", "uav-2")
