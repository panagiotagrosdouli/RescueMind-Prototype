"""Frontier detection and multi-agent exploration planning for synthetic maps.

The planner operates on a discrete occupancy grid. It does not generate collision-free
trajectories or control physical robots.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import hypot

import numpy as np

from .models import Agent, Pose2D

UNKNOWN = -1
FREE = 0
OCCUPIED = 1


@dataclass(frozen=True)
class Frontier:
    frontier_id: str
    cells: tuple[tuple[int, int], ...]
    centroid: Pose2D
    information_gain: float
    hazard: float
    survivor_interest: float
    communication_quality: float


@dataclass(frozen=True)
class FrontierBid:
    agent_id: str
    frontier_id: str
    feasible: bool
    utility: float
    travel_distance: float
    reason: str | None = None


@dataclass(frozen=True)
class FrontierAssignment:
    agent_id: str
    frontier_id: str
    utility: float


@dataclass(frozen=True)
class FrontierPlan:
    frontiers: tuple[Frontier, ...]
    assignments: tuple[FrontierAssignment, ...]
    unassigned_frontiers: tuple[str, ...]
    idle_agents: tuple[str, ...]
    bids: tuple[FrontierBid, ...]


class FrontierExplorer:
    """Detect, score, and assign exploration frontiers."""

    def __init__(
        self,
        min_cluster_size: int = 1,
        information_radius: int = 2,
        travel_weight: float = 0.05,
        hazard_weight: float = 0.35,
        communication_weight: float = 0.20,
        survivor_weight: float = 0.30,
        unassigned_penalty: float = 0.10,
        max_frontiers: int = 18,
    ):
        if min_cluster_size < 1 or information_radius < 1:
            raise ValueError("cluster size and information radius must be positive")
        self.min_cluster_size = min_cluster_size
        self.information_radius = information_radius
        self.travel_weight = travel_weight
        self.hazard_weight = hazard_weight
        self.communication_weight = communication_weight
        self.survivor_weight = survivor_weight
        self.unassigned_penalty = unassigned_penalty
        self.max_frontiers = max_frontiers

    @staticmethod
    def _validate_grid(grid: np.ndarray) -> None:
        if grid.ndim != 2 or grid.size == 0:
            raise ValueError("occupancy grid must be a non-empty 2D array")
        if not np.isin(grid, [UNKNOWN, FREE, OCCUPIED]).all():
            raise ValueError("occupancy grid values must be -1, 0, or 1")

    @staticmethod
    def _neighbors(y: int, x: int, height: int, width: int):
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width:
                yield ny, nx

    def frontier_mask(self, grid: np.ndarray) -> np.ndarray:
        """Return free cells adjacent to at least one unknown cell."""

        self._validate_grid(grid)
        height, width = grid.shape
        mask = np.zeros_like(grid, dtype=bool)
        for y in range(height):
            for x in range(width):
                if grid[y, x] != FREE:
                    continue
                mask[y, x] = any(
                    grid[ny, nx] == UNKNOWN
                    for ny, nx in self._neighbors(y, x, height, width)
                )
        return mask

    def _cluster(self, mask: np.ndarray) -> list[list[tuple[int, int]]]:
        height, width = mask.shape
        visited: set[tuple[int, int]] = set()
        clusters: list[list[tuple[int, int]]] = []
        for y, x in zip(*np.nonzero(mask), strict=True):
            start = (int(y), int(x))
            if start in visited:
                continue
            stack = [start]
            visited.add(start)
            cluster: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                cluster.append((cy, cx))
                for neighbor in self._neighbors(cy, cx, height, width):
                    if mask[neighbor] and neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            if len(cluster) >= self.min_cluster_size:
                clusters.append(sorted(cluster))
        return clusters

    def _information_gain(self, grid: np.ndarray, cells: list[tuple[int, int]]) -> float:
        height, width = grid.shape
        unknown: set[tuple[int, int]] = set()
        for y, x in cells:
            for ny in range(max(0, y - self.information_radius), min(height, y + self.information_radius + 1)):
                for nx in range(max(0, x - self.information_radius), min(width, x + self.information_radius + 1)):
                    if grid[ny, nx] == UNKNOWN:
                        unknown.add((ny, nx))
        return float(len(unknown))

    def detect(
        self,
        grid: np.ndarray,
        hazard_map: np.ndarray | None = None,
        survivor_map: np.ndarray | None = None,
        communication_map: np.ndarray | None = None,
    ) -> list[Frontier]:
        """Detect connected frontier clusters and attach map-derived attributes."""

        self._validate_grid(grid)
        shape = grid.shape
        hazard = np.zeros(shape) if hazard_map is None else np.asarray(hazard_map, dtype=float)
        survivor = np.zeros(shape) if survivor_map is None else np.asarray(survivor_map, dtype=float)
        communication = np.ones(shape) if communication_map is None else np.asarray(communication_map, dtype=float)
        if any(layer.shape != shape for layer in (hazard, survivor, communication)):
            raise ValueError("all map layers must match the occupancy grid shape")

        frontiers: list[Frontier] = []
        for index, cluster in enumerate(self._cluster(self.frontier_mask(grid))):
            ys = np.array([cell[0] for cell in cluster])
            xs = np.array([cell[1] for cell in cluster])
            frontiers.append(
                Frontier(
                    frontier_id=f"frontier-{index}",
                    cells=tuple(cluster),
                    centroid=Pose2D(float(xs.mean()), float(ys.mean())),
                    information_gain=self._information_gain(grid, cluster),
                    hazard=float(np.clip(hazard[ys, xs].mean(), 0.0, 1.0)),
                    survivor_interest=float(np.clip(survivor[ys, xs].mean(), 0.0, 1.0)),
                    communication_quality=float(np.clip(communication[ys, xs].mean(), 0.0, 1.0)),
                )
            )
        return frontiers

    def bid(self, agent: Agent, frontier: Frontier) -> FrontierBid:
        if agent.failed:
            return FrontierBid(agent.agent_id, frontier.frontier_id, False, float("-inf"), 0.0, "agent_failed")
        if agent.speed <= 0.0:
            return FrontierBid(agent.agent_id, frontier.frontier_id, False, float("-inf"), 0.0, "invalid_speed")
        distance = hypot(agent.pose.x - frontier.centroid.x, agent.pose.y - frontier.centroid.y)
        travel_time = distance / agent.speed
        battery_required = min(1.0, travel_time / 600.0)
        if agent.battery < battery_required:
            return FrontierBid(agent.agent_id, frontier.frontier_id, False, float("-inf"), distance, "insufficient_battery")
        utility = (
            frontier.information_gain
            + self.survivor_weight * frontier.survivor_interest
            + self.communication_weight * frontier.communication_quality
            - self.hazard_weight * frontier.hazard
            - self.travel_weight * distance
        )
        return FrontierBid(agent.agent_id, frontier.frontier_id, True, float(utility), distance)

    def plan(self, agents: list[Agent], frontiers: list[Frontier]) -> FrontierPlan:
        """Compute an exact one-agent-to-one-frontier assignment for small teams."""

        if len(frontiers) > self.max_frontiers:
            raise ValueError(f"at most {self.max_frontiers} frontiers are supported")
        ordered_agents = sorted(agents, key=lambda item: item.agent_id)
        ordered_frontiers = sorted(frontiers, key=lambda item: item.frontier_id)
        bids = tuple(self.bid(agent, frontier) for agent in ordered_agents for frontier in ordered_frontiers)
        lookup = {(bid.agent_id, bid.frontier_id): bid for bid in bids}

        @lru_cache(maxsize=None)
        def solve(agent_index: int, used_mask: int):
            if agent_index == len(ordered_agents):
                unassigned = len(ordered_frontiers) - used_mask.bit_count()
                return -self.unassigned_penalty * unassigned, ()
            best_score, best_pairs = solve(agent_index + 1, used_mask)
            agent = ordered_agents[agent_index]
            for frontier_index, frontier in enumerate(ordered_frontiers):
                bit = 1 << frontier_index
                bid = lookup[(agent.agent_id, frontier.frontier_id)]
                if used_mask & bit or not bid.feasible:
                    continue
                score, pairs = solve(agent_index + 1, used_mask | bit)
                candidate = score + bid.utility
                candidate_pairs = ((agent.agent_id, frontier.frontier_id, bid.utility),) + pairs
                if candidate > best_score or (candidate == best_score and candidate_pairs < best_pairs):
                    best_score, best_pairs = candidate, candidate_pairs
            return best_score, best_pairs

        _, pairs = solve(0, 0)
        assignments = tuple(FrontierAssignment(*pair) for pair in pairs)
        assigned_agents = {item.agent_id for item in assignments}
        assigned_frontiers = {item.frontier_id for item in assignments}
        return FrontierPlan(
            frontiers=tuple(ordered_frontiers),
            assignments=assignments,
            unassigned_frontiers=tuple(
                item.frontier_id for item in ordered_frontiers if item.frontier_id not in assigned_frontiers
            ),
            idle_agents=tuple(item.agent_id for item in ordered_agents if item.agent_id not in assigned_agents),
            bids=bids,
        )
