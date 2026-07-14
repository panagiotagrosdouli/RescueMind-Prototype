import pytest

from rescuemind.allocation import InspectionTask, RiskAwareAllocator
from rescuemind.models import Agent, Hypothesis, Pose2D, PriorityEstimate


def agent(
    agent_id: str,
    x: float,
    sensors: list[str],
    battery: float = 0.8,
    failed: bool = False,
) -> Agent:
    return Agent(
        agent_id=agent_id,
        kind="UAV",
        pose=Pose2D(x, 0.0),
        speed=2.0,
        battery=battery,
        comm_range=100.0,
        sensors=sensors,
        failed=failed,
    )


def hypothesis(hypothesis_id: str, x: float) -> Hypothesis:
    return Hypothesis(hypothesis_id, Pose2D(x, 0.0), 0.8, 0.2)


def priority(hypothesis_id: str, low: float = 0.6) -> PriorityEstimate:
    return PriorityEstimate(hypothesis_id, low + 0.1, low, low + 0.2, {}, 0.2)


def test_bid_rejects_failed_agent() -> None:
    allocator = RiskAwareAllocator()
    task = InspectionTask("T-1", "H-1", frozenset({"thermal"}))
    bid = allocator.bid(
        agent("A-1", 0.0, ["thermal"], failed=True),
        task,
        hypothesis("H-1", 1.0),
        priority("H-1"),
        1.0,
    )
    assert not bid.feasible
    assert bid.rejection_reason == "agent_failed"


def test_bid_rejects_insufficient_battery() -> None:
    allocator = RiskAwareAllocator()
    task = InspectionTask(
        "T-1", "H-1", frozenset({"thermal"}), minimum_battery=0.5
    )
    bid = allocator.bid(
        agent("A-1", 0.0, ["thermal"], battery=0.2),
        task,
        hypothesis("H-1", 1.0),
        priority("H-1"),
        1.0,
    )
    assert not bid.feasible
    assert bid.rejection_reason == "insufficient_battery"


def test_bid_rejects_missing_capability() -> None:
    allocator = RiskAwareAllocator()
    task = InspectionTask("T-1", "H-1", frozenset({"radar"}))
    bid = allocator.bid(
        agent("A-1", 0.0, ["thermal"]),
        task,
        hypothesis("H-1", 1.0),
        priority("H-1"),
        1.0,
    )
    assert not bid.feasible
    assert bid.rejection_reason == "missing_required_capability"


def test_higher_risk_reduces_bid_utility() -> None:
    allocator = RiskAwareAllocator()
    robot = agent("A-1", 0.0, ["thermal"])
    target = hypothesis("H-1", 1.0)
    estimate = priority("H-1")
    safe = allocator.bid(
        robot,
        InspectionTask("safe", "H-1", frozenset({"thermal"}), risk=0.1),
        target,
        estimate,
        1.0,
    )
    dangerous = allocator.bid(
        robot,
        InspectionTask("danger", "H-1", frozenset({"thermal"}), risk=0.9),
        target,
        estimate,
        1.0,
    )
    assert dangerous.utility < safe.utility


def test_global_allocation_uses_distinct_agents_and_tasks() -> None:
    allocator = RiskAwareAllocator()
    agents = [
        agent("near-left", 0.0, ["thermal"]),
        agent("near-right", 10.0, ["radar"]),
    ]
    tasks = [
        InspectionTask("T-left", "H-left", frozenset({"thermal"})),
        InspectionTask("T-right", "H-right", frozenset({"radar"})),
    ]
    hypotheses = {
        "H-left": hypothesis("H-left", 1.0),
        "H-right": hypothesis("H-right", 9.0),
    }
    priorities = {
        "H-left": priority("H-left"),
        "H-right": priority("H-right"),
    }
    result = allocator.allocate(agents, tasks, hypotheses, priorities)
    pairs = {(item.agent_id, item.task_id) for item in result.assignments}
    assert pairs == {("near-left", "T-left"), ("near-right", "T-right")}
    assert not result.unassigned_task_ids
    assert not result.idle_agent_ids


def test_infeasible_task_remains_unassigned() -> None:
    allocator = RiskAwareAllocator()
    result = allocator.allocate(
        [agent("A-1", 0.0, ["thermal"])],
        [InspectionTask("T-1", "H-1", frozenset({"radar"}))],
        {"H-1": hypothesis("H-1", 1.0)},
        {"H-1": priority("H-1")},
    )
    assert result.assignments == ()
    assert result.unassigned_task_ids == ("T-1",)
    assert result.idle_agent_ids == ("A-1",)


def test_missing_hypothesis_or_priority_is_explicit() -> None:
    allocator = RiskAwareAllocator()
    with pytest.raises(KeyError, match="missing hypothesis or priority"):
        allocator.allocate(
            [agent("A-1", 0.0, ["thermal"])],
            [InspectionTask("T-1", "H-1", frozenset({"thermal"}))],
            {},
            {},
        )


def test_large_exact_problem_is_rejected() -> None:
    allocator = RiskAwareAllocator()
    tasks = [
        InspectionTask(f"T-{index}", "H-1", frozenset())
        for index in range(19)
    ]
    with pytest.raises(ValueError, match="at most 18 tasks"):
        allocator.allocate([], tasks, {"H-1": hypothesis("H-1", 0.0)}, {"H-1": priority("H-1")})


def test_negative_penalty_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        RiskAwareAllocator(risk_penalty=-0.1)
