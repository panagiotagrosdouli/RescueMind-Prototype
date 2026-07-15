"""Collaborative active-perception planning for synthetic multi-agent experiments.

The planner operates on explicit candidate viewpoints and uncertainty values. It is
not a motion planner, collision-avoidance system, or hardware-validated autonomy
component.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import hypot

import numpy as np

from .models import Agent, Pose2D


@dataclass(frozen=True)
class PerceptionTarget:
    target_id: str
    pose: Pose2D
    uncertainty: float
    required_modalities: tuple[str, ...] = ()
    priority: float = 0.5
    last_observed_at: float | None = None


@dataclass(frozen=True)
class Viewpoint:
    viewpoint_id: str
    target_id: str
    pose: Pose2D
    expected_quality: float
    visible_modalities: tuple[str, ...]
    communication_quality: float = 1.0
    risk: float = 0.0


@dataclass(frozen=True)
class PerceptionBid:
    agent_id: str
    viewpoint_id: str
    target_id: str
    utility: float
    information_gain: float
    travel_cost: float
    overlap_penalty: float
    feasible: bool
    rejection_reason: str | None = None


@dataclass(frozen=True)
class PerceptionAssignment:
    agent_id: str
    viewpoint_id: str
    target_id: str
    utility: float


@dataclass(frozen=True)
class PerceptionPlan:
    assignments: tuple[PerceptionAssignment, ...]
    unassigned_target_ids: tuple[str, ...]
    idle_agent_ids: tuple[str, ...]
    total_utility: float


class CollaborativePerceptionPlanner:
    """Coordinate small teams to reduce uncertainty without duplicate coverage."""

    def __init__(
        self,
        travel_weight: float = 0.08,
        overlap_weight: float = 0.35,
        risk_weight: float = 0.20,
        communication_weight: float = 0.15,
        unassigned_penalty: float = 0.25,
    ):
        values = (
            travel_weight,
            overlap_weight,
            risk_weight,
            communication_weight,
            unassigned_penalty,
        )
        if any(value < 0.0 for value in values):
            raise ValueError("planner weights must be non-negative")
        self.travel_weight = travel_weight
        self.overlap_weight = overlap_weight
        self.risk_weight = risk_weight
        self.communication_weight = communication_weight
        self.unassigned_penalty = unassigned_penalty

    @staticmethod
    def fuse_uncertainty(prior: float, observation_quality: float) -> float:
        """Return a bounded scalar posterior uncertainty approximation."""

        prior_clipped = float(np.clip(prior, 0.0, 1.0))
        quality = float(np.clip(observation_quality, 0.0, 1.0))
        return float(np.clip(prior_clipped * (1.0 - 0.75 * quality), 0.0, 1.0))

    @classmethod
    def information_gain(cls, prior: float, observation_quality: float) -> float:
        posterior = cls.fuse_uncertainty(prior, observation_quality)
        return float(max(0.0, prior - posterior))

    @staticmethod
    def _modality_coverage(agent: Agent, target: PerceptionTarget, viewpoint: Viewpoint) -> float:
        required = set(target.required_modalities)
        if not required:
            return 1.0
        available = set(agent.sensors) & set(viewpoint.visible_modalities)
        return len(required & available) / len(required)

    def bid(
        self,
        agent: Agent,
        target: PerceptionTarget,
        viewpoint: Viewpoint,
        reserved_viewpoints: tuple[Viewpoint, ...] = (),
    ) -> PerceptionBid:
        if viewpoint.target_id != target.target_id:
            raise ValueError("viewpoint target does not match target")
        if agent.failed:
            return PerceptionBid(
                agent.agent_id,
                viewpoint.viewpoint_id,
                target.target_id,
                0.0,
                0.0,
                0.0,
                0.0,
                False,
                "agent_failed",
            )
        coverage = self._modality_coverage(agent, target, viewpoint)
        if coverage <= 0.0:
            return PerceptionBid(
                agent.agent_id,
                viewpoint.viewpoint_id,
                target.target_id,
                0.0,
                0.0,
                0.0,
                0.0,
                False,
                "missing_required_modality",
            )
        distance = hypot(agent.pose.x - viewpoint.pose.x, agent.pose.y - viewpoint.pose.y)
        travel_cost = distance / max(agent.speed, 0.1)
        gain = self.information_gain(target.uncertainty, viewpoint.expected_quality) * coverage
        overlap = 0.0
        for reserved in reserved_viewpoints:
            separation = hypot(viewpoint.pose.x - reserved.pose.x, viewpoint.pose.y - reserved.pose.y)
            if viewpoint.target_id == reserved.target_id:
                overlap = max(overlap, max(0.0, 1.0 - separation / 5.0))
        communication_penalty = 1.0 - float(np.clip(viewpoint.communication_quality, 0.0, 1.0))
        utility = (
            float(np.clip(target.priority, 0.0, 1.0)) * gain
            - self.travel_weight * min(1.0, travel_cost / 120.0)
            - self.overlap_weight * overlap
            - self.risk_weight * float(np.clip(viewpoint.risk, 0.0, 1.0))
            - self.communication_weight * communication_penalty
        )
        return PerceptionBid(
            agent.agent_id,
            viewpoint.viewpoint_id,
            target.target_id,
            float(utility),
            float(gain),
            float(travel_cost),
            float(overlap),
            True,
        )

    def plan(
        self,
        agents: list[Agent],
        targets: list[PerceptionTarget],
        viewpoints: list[Viewpoint],
    ) -> PerceptionPlan:
        """Find an exact one-agent-to-one-target plan for small candidate sets."""

        if len(targets) > 18:
            raise ValueError("exact planner supports at most 18 targets")
        by_target: dict[str, list[Viewpoint]] = {target.target_id: [] for target in targets}
        for viewpoint in viewpoints:
            if viewpoint.target_id in by_target:
                by_target[viewpoint.target_id].append(viewpoint)

        feasible: dict[tuple[int, int, int], PerceptionBid] = {}
        for agent_index, agent in enumerate(agents):
            for target_index, target in enumerate(targets):
                for view_index, viewpoint in enumerate(by_target[target.target_id]):
                    candidate = self.bid(agent, target, viewpoint)
                    if candidate.feasible:
                        feasible[(agent_index, target_index, view_index)] = candidate

        @lru_cache(maxsize=None)
        def solve(agent_index: int, used_targets: int) -> tuple[float, tuple[tuple[int, int, int], ...]]:
            if agent_index == len(agents):
                missing = len(targets) - used_targets.bit_count()
                return -self.unassigned_penalty * missing, ()
            best_value, best_items = solve(agent_index + 1, used_targets)
            for target_index, target in enumerate(targets):
                if used_targets & (1 << target_index):
                    continue
                for view_index, _ in enumerate(by_target[target.target_id]):
                    candidate = feasible.get((agent_index, target_index, view_index))
                    if candidate is None:
                        continue
                    remainder, items = solve(agent_index + 1, used_targets | (1 << target_index))
                    total = candidate.utility + remainder
                    if total > best_value:
                        best_value = total
                        best_items = ((agent_index, target_index, view_index),) + items
            return best_value, best_items

        total, selected = solve(0, 0)
        assignments = tuple(
            PerceptionAssignment(
                agents[agent_index].agent_id,
                by_target[targets[target_index].target_id][view_index].viewpoint_id,
                targets[target_index].target_id,
                feasible[(agent_index, target_index, view_index)].utility,
            )
            for agent_index, target_index, view_index in selected
        )
        assigned_targets = {item.target_id for item in assignments}
        assigned_agents = {item.agent_id for item in assignments}
        return PerceptionPlan(
            assignments,
            tuple(target.target_id for target in targets if target.target_id not in assigned_targets),
            tuple(agent.agent_id for agent in agents if agent.agent_id not in assigned_agents),
            float(total),
        )
