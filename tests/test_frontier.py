from __future__ import annotations

import numpy as np
import pytest

from rescuemind.frontier import (
    FREE,
    OCCUPIED,
    UNKNOWN,
    Frontier,
    FrontierExplorer,
)
from rescuemind.models import Agent, Pose2D


def agent(
    agent_id: str,
    x: float = 0.0,
    y: float = 0.0,
    *,
    battery: float = 1.0,
    failed: bool = False,
) -> Agent:
    return Agent(
        agent_id=agent_id,
        kind="uav",
        pose=Pose2D(x, y),
        speed=1.0,
        battery=battery,
        comm_range=100.0,
        sensors=["rgb"],
        failed=failed,
    )


def frontier(frontier_id: str, x: float, information_gain: float = 2.0) -> Frontier:
    return Frontier(
        frontier_id=frontier_id,
        cells=((0, int(x)),),
        centroid=Pose2D(x, 0.0),
        information_gain=information_gain,
        hazard=0.0,
        survivor_interest=0.0,
        communication_quality=1.0,
    )


def test_frontier_mask_marks_free_cells_next_to_unknown_space() -> None:
    grid = np.array(
        [
            [OCCUPIED, UNKNOWN, UNKNOWN],
            [OCCUPIED, FREE, UNKNOWN],
            [OCCUPIED, FREE, FREE],
        ]
    )
    mask = FrontierExplorer().frontier_mask(grid)
    assert mask.tolist() == [
        [False, False, False],
        [False, True, False],
        [False, False, True],
    ]


def test_detection_groups_connected_frontier_cells() -> None:
    grid = np.array(
        [
            [UNKNOWN, UNKNOWN, UNKNOWN, OCCUPIED],
            [FREE, FREE, FREE, OCCUPIED],
            [OCCUPIED, OCCUPIED, OCCUPIED, OCCUPIED],
        ]
    )
    frontiers = FrontierExplorer().detect(grid)
    assert len(frontiers) == 1
    assert len(frontiers[0].cells) == 3
    assert frontiers[0].information_gain == 3.0


def test_detection_reads_hazard_survivor_and_communication_layers() -> None:
    grid = np.array([[UNKNOWN, UNKNOWN], [FREE, FREE]])
    hazard = np.array([[0.0, 0.0], [0.2, 0.6]])
    survivor = np.array([[0.0, 0.0], [0.5, 0.9]])
    communication = np.array([[1.0, 1.0], [0.4, 0.8]])
    detected = FrontierExplorer().detect(grid, hazard, survivor, communication)[0]
    assert detected.hazard == pytest.approx(0.4)
    assert detected.survivor_interest == pytest.approx(0.7)
    assert detected.communication_quality == pytest.approx(0.6)


def test_complete_map_has_no_frontiers() -> None:
    grid = np.array([[FREE, FREE], [FREE, OCCUPIED]])
    assert FrontierExplorer().detect(grid) == []


def test_invalid_grid_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="values"):
        FrontierExplorer().detect(np.array([[2]]))


def test_failed_agent_produces_infeasible_bid() -> None:
    bid = FrontierExplorer().bid(agent("uav-1", failed=True), frontier("f-1", 1.0))
    assert not bid.feasible
    assert bid.reason == "agent_failed"


def test_higher_hazard_reduces_frontier_utility() -> None:
    explorer = FrontierExplorer()
    safe = frontier("safe", 1.0)
    risky = Frontier(
        frontier_id="risky",
        cells=((0, 1),),
        centroid=Pose2D(1.0, 0.0),
        information_gain=2.0,
        hazard=1.0,
        survivor_interest=0.0,
        communication_quality=1.0,
    )
    assert explorer.bid(agent("uav-1"), safe).utility > explorer.bid(
        agent("uav-1"), risky
    ).utility


def test_plan_uses_distinct_agents_and_frontiers() -> None:
    explorer = FrontierExplorer()
    plan = explorer.plan(
        [agent("left", 0.0), agent("right", 10.0)],
        [frontier("f-left", 1.0), frontier("f-right", 9.0)],
    )
    pairs = {(item.agent_id, item.frontier_id) for item in plan.assignments}
    assert pairs == {("left", "f-left"), ("right", "f-right")}
    assert plan.unassigned_frontiers == ()
    assert plan.idle_agents == ()


def test_plan_reports_unassigned_frontiers_and_idle_agents() -> None:
    explorer = FrontierExplorer()
    one_agent = explorer.plan(
        [agent("uav-1")],
        [frontier("f-1", 1.0), frontier("f-2", 2.0)],
    )
    assert len(one_agent.assignments) == 1
    assert len(one_agent.unassigned_frontiers) == 1

    failed_only = explorer.plan([agent("failed", failed=True)], [frontier("f-1", 1.0)])
    assert failed_only.assignments == ()
    assert failed_only.unassigned_frontiers == ("f-1",)
    assert failed_only.idle_agents == ("failed",)


def test_frontier_limit_is_explicit() -> None:
    explorer = FrontierExplorer(max_frontiers=1)
    with pytest.raises(ValueError, match="at most 1"):
        explorer.plan([agent("uav-1")], [frontier("a", 1.0), frontier("b", 2.0)])
