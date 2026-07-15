from rescuemind.active_perception import (
    CollaborativePerceptionPlanner,
    PerceptionTarget,
    Viewpoint,
)
from rescuemind.models import Agent, Pose2D


def agent(agent_id: str, x: float, sensors: list[str], failed: bool = False) -> Agent:
    return Agent(agent_id, "uav", Pose2D(x, 0.0), 2.0, 0.8, 100.0, sensors, failed=failed)


def target(target_id: str, x: float, uncertainty: float = 0.8) -> PerceptionTarget:
    return PerceptionTarget(target_id, Pose2D(x, 0.0), uncertainty, ("thermal",), 1.0)


def view(view_id: str, target_id: str, x: float, quality: float = 0.8) -> Viewpoint:
    return Viewpoint(view_id, target_id, Pose2D(x, 0.0), quality, ("thermal",))


def test_uncertainty_decreases_with_quality() -> None:
    planner = CollaborativePerceptionPlanner()
    assert planner.fuse_uncertainty(0.8, 0.9) < planner.fuse_uncertainty(0.8, 0.2)


def test_information_gain_is_non_negative() -> None:
    planner = CollaborativePerceptionPlanner()
    assert planner.information_gain(0.7, 0.8) >= 0.0


def test_failed_agent_is_rejected() -> None:
    bid = CollaborativePerceptionPlanner().bid(
        agent("a", 0.0, ["thermal"], failed=True), target("t", 1.0), view("v", "t", 1.0)
    )
    assert not bid.feasible
    assert bid.rejection_reason == "agent_failed"


def test_missing_modality_is_rejected() -> None:
    bid = CollaborativePerceptionPlanner().bid(
        agent("a", 0.0, ["rgb"]), target("t", 1.0), view("v", "t", 1.0)
    )
    assert not bid.feasible
    assert bid.rejection_reason == "missing_required_modality"


def test_overlap_penalizes_duplicate_view() -> None:
    planner = CollaborativePerceptionPlanner()
    candidate = view("v", "t", 1.0)
    without_overlap = planner.bid(agent("a", 0.0, ["thermal"]), target("t", 1.0), candidate)
    with_overlap = planner.bid(
        agent("a", 0.0, ["thermal"]),
        target("t", 1.0),
        candidate,
        reserved_viewpoints=(view("other", "t", 1.5),),
    )
    assert with_overlap.utility < without_overlap.utility


def test_plan_assigns_distinct_targets() -> None:
    result = CollaborativePerceptionPlanner().plan(
        [agent("a1", 0.0, ["thermal"]), agent("a2", 10.0, ["thermal"])],
        [target("t1", 1.0), target("t2", 9.0)],
        [view("v1", "t1", 1.0), view("v2", "t2", 9.0)],
    )
    assert len(result.assignments) == 2
    assert len({item.target_id for item in result.assignments}) == 2


def test_plan_leaves_infeasible_target_unassigned() -> None:
    result = CollaborativePerceptionPlanner().plan(
        [agent("a", 0.0, ["rgb"])],
        [target("t", 1.0)],
        [view("v", "t", 1.0)],
    )
    assert result.unassigned_target_ids == ("t",)
    assert result.idle_agent_ids == ("a",)


def test_target_viewpoint_mismatch_raises() -> None:
    planner = CollaborativePerceptionPlanner()
    try:
        planner.bid(agent("a", 0.0, ["thermal"]), target("t1", 1.0), view("v", "t2", 1.0))
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_large_exact_problem_is_rejected() -> None:
    planner = CollaborativePerceptionPlanner()
    targets = [target(f"t-{index}", float(index)) for index in range(19)]
    try:
        planner.plan([], targets, [])
    except ValueError as exc:
        assert "at most 18" in str(exc)
    else:
        raise AssertionError("expected ValueError")
