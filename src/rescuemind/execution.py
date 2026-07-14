"""Failure-aware task execution state machine for synthetic missions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskState(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    RETRY_PENDING = "RETRY_PENDING"
    REASSIGNMENT_REQUIRED = "REASSIGNMENT_REQUIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ExecutionEvent:
    task_id: str
    timestamp: float
    previous_state: TaskState
    new_state: TaskState
    reason: str
    agent_id: str | None
    attempt: int


@dataclass
class MissionTask:
    task_id: str
    max_attempts: int = 3
    state: TaskState = TaskState.PENDING
    assigned_agent_id: str | None = None
    attempt: int = 0
    last_update: float = 0.0
    history: list[ExecutionEvent] = field(default_factory=list)


class MissionExecutor:
    """Apply explicit, auditable transitions to mission tasks."""

    _allowed = {
        TaskState.PENDING: {TaskState.ASSIGNED, TaskState.CANCELLED},
        TaskState.ASSIGNED: {TaskState.IN_PROGRESS, TaskState.REASSIGNMENT_REQUIRED, TaskState.CANCELLED},
        TaskState.IN_PROGRESS: {
            TaskState.SUCCEEDED,
            TaskState.RETRY_PENDING,
            TaskState.REASSIGNMENT_REQUIRED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        },
        TaskState.RETRY_PENDING: {TaskState.ASSIGNED, TaskState.FAILED, TaskState.CANCELLED},
        TaskState.REASSIGNMENT_REQUIRED: {TaskState.ASSIGNED, TaskState.FAILED, TaskState.CANCELLED},
        TaskState.SUCCEEDED: set(),
        TaskState.FAILED: set(),
        TaskState.CANCELLED: set(),
    }

    @classmethod
    def transition(
        cls,
        task: MissionTask,
        new_state: TaskState,
        timestamp: float,
        reason: str,
        agent_id: str | None = None,
    ) -> ExecutionEvent:
        if timestamp < task.last_update:
            raise ValueError("task updates must be monotonic")
        if new_state not in cls._allowed[task.state]:
            raise ValueError(f"invalid transition {task.state} -> {new_state}")
        if new_state == TaskState.ASSIGNED:
            if not agent_id:
                raise ValueError("ASSIGNED requires agent_id")
            task.assigned_agent_id = agent_id
            task.attempt += 1
            if task.attempt > task.max_attempts:
                raise ValueError("maximum attempts exceeded")
        if new_state in {TaskState.REASSIGNMENT_REQUIRED, TaskState.RETRY_PENDING}:
            task.assigned_agent_id = None
        previous = task.state
        task.state = new_state
        task.last_update = timestamp
        event = ExecutionEvent(
            task.task_id,
            timestamp,
            previous,
            new_state,
            reason,
            agent_id,
            task.attempt,
        )
        task.history.append(event)
        return event

    @classmethod
    def report_failure(
        cls,
        task: MissionTask,
        timestamp: float,
        reason: str,
        recoverable: bool,
        agent_failed: bool = False,
    ) -> ExecutionEvent:
        if task.state != TaskState.IN_PROGRESS:
            raise ValueError("failures can only be reported while IN_PROGRESS")
        if agent_failed:
            target = TaskState.REASSIGNMENT_REQUIRED
        elif recoverable and task.attempt < task.max_attempts:
            target = TaskState.RETRY_PENDING
        else:
            target = TaskState.FAILED
        return cls.transition(task, target, timestamp, reason)
