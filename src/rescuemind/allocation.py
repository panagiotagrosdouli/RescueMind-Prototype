"""Risk-aware multi-agent task allocation for synthetic research scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import hypot

from .models import Agent, Hypothesis, PriorityEstimate


@dataclass(frozen=True)
class InspectionTask:
    """A verification or inspection task derived from one hypothesis."""

    task_id: str
    hypothesis_id: str
    required_modalities: frozenset[str]
    minimum_battery: float = 0.15
    minimum_communication_quality: float = 0.0
    risk: float = 0.0


@dataclass(frozen=True)
class AgentTaskBid:
    """Transparent utility estimate for assigning one agent to one task."""

    agent_id: str
    task_id: str
    utility: float
    travel_time: float
    capability_coverage: float
    battery_margin: float
    communication_quality: float
    feasible: bool
    rejection_reason: str | None = None


@dataclass(frozen=True)
class TaskAssignment:
    agent_id: str
    task_id: str
    utility: float


@dataclass(frozen=True)
class AllocationResult:
    assignments: tuple[TaskAssignment, ...]
    unassigned_task_ids: tuple[str, ...]
    idle_agent_ids: tuple[str, ...]
    total_utility: float


class RiskAwareAllocator:
    """Compute globally consistent one-agent-to-one-task assignments.

    The exact dynamic-programming solver is intended for small synthetic fleets.
    It raises above 18 tasks rather than silently incurring exponential runtime.
    """

    def __init__(
        self,
        travel_penalty: float = 0.08,
        risk_penalty: float = 0.20,
        communication_penalty: float = 0.10,
        unassigned_penalty: float = 0.05,
    ):
        if any(
            value < 0.0
            for value in (
                travel_penalty,
                risk_penalty,
                communication_penalty,
                unassigned_penalty,
            )
        ):
            raise ValueError("allocation penalties must be non-negative")
        self.travel_penalty = travel_penalty
        self.risk_penalty = risk_penalty
        self.communication_penalty = communication_penalty
        self.unassigned_penalty = unassigned_penalty

    @staticmethod
    def _clip(value: float) -> float:
        return min(1.0, max(0.0, float(value)))

    def bid(
        self,
        agent: Agent,
        task: InspectionTask,
        hypothesis: Hypothesis,
        priority: PriorityEstimate,
        communication_quality: float,
    ) -> AgentTaskBid:
        """Return an auditable bid or an explicit infeasibility reason."""

        communication_quality = self._clip(communication_quality)
        battery = self._clip(agent.battery)
        risk = self._clip(task.risk)

        if agent.failed:
            return AgentTaskBid(
                agent.agent_id,
                task.task_id,
                float("-inf"),
                float("inf"),
                0.0,
                battery - task.minimum_battery,
                communication_quality,
                False,
                "agent_failed",
            )
        if battery < task.minimum_battery:
            return AgentTaskBid(
                agent.agent_id,
                task.task_id,
                float("-inf"),
                float("inf"),
                0.0,
                battery - task.minimum_battery,
                communication_quality,
                False,
                "insufficient_battery",
            )
        if communication_quality < task.minimum_communication_quality:
            return AgentTaskBid(
                agent.agent_id,
                task.task_id,
                float("-inf"),
                float("inf"),
                0.0,
                battery - task.minimum_battery,
                communication_quality,
                False,
                "insufficient_communication",
            )

        required = task.required_modalities
        available = set(agent.sensors)
        capability_coverage = (
            len(required & available) / len(required) if required else 1.0
        )
        if required and capability_coverage == 0.0:
            return AgentTaskBid(
                agent.agent_id,
                task.task_id,
                float("-inf"),
                float("inf"),
                0.0,
                battery - task.minimum_battery,
                communication_quality,
                False,
                "missing_required_capability",
            )

        distance = hypot(agent.pose.x - hypothesis.pose.x, agent.pose.y - hypothesis.pose.y)
        travel_time = distance / max(agent.speed, 0.1)
        travel_cost = min(1.0, travel_time / 300.0)
        battery_margin = battery - task.minimum_battery

        utility = (
            0.48 * priority.low
            + 0.22 * capability_coverage
            + 0.12 * battery_margin
            + 0.08 * communication_quality
            - self.travel_penalty * travel_cost
            - self.risk_penalty * risk
            - self.communication_penalty * (1.0 - communication_quality)
        )
        return AgentTaskBid(
            agent.agent_id,
            task.task_id,
            float(utility),
            float(travel_time),
            float(capability_coverage),
            float(battery_margin),
            float(communication_quality),
            True,
        )

    def allocate(
        self,
        agents: list[Agent],
        tasks: list[InspectionTask],
        hypotheses: dict[str, Hypothesis],
        priorities: dict[str, PriorityEstimate],
        communication_quality: dict[str, float] | None = None,
    ) -> AllocationResult:
        """Maximize total bid utility subject to one-to-one assignment."""

        if len(tasks) > 18:
            raise ValueError("exact allocation supports at most 18 tasks")
        communication_quality = communication_quality or {}

        bids: dict[tuple[int, int], AgentTaskBid] = {}
        for agent_index, agent in enumerate(agents):
            for task_index, task in enumerate(tasks):
                try:
                    hypothesis = hypotheses[task.hypothesis_id]
                    priority = priorities[task.hypothesis_id]
                except KeyError as exc:
                    raise KeyError(
                        f"missing hypothesis or priority for task {task.task_id}"
                    ) from exc
                bid = self.bid(
                    agent,
                    task,
                    hypothesis,
                    priority,
                    communication_quality.get(agent.agent_id, 1.0),
                )
                if bid.feasible:
                    bids[(agent_index, task_index)] = bid

        @lru_cache(maxsize=None)
        def solve(agent_index: int, used_mask: int) -> tuple[float, tuple[tuple[int, int], ...]]:
            if agent_index == len(agents):
                unassigned = len(tasks) - used_mask.bit_count()
                return -self.unassigned_penalty * unassigned, ()

            best_utility, best_pairs = solve(agent_index + 1, used_mask)
            for task_index in range(len(tasks)):
                if used_mask & (1 << task_index):
                    continue
                bid = bids.get((agent_index, task_index))
                if bid is None:
                    continue
                remainder, pairs = solve(agent_index + 1, used_mask | (1 << task_index))
                total = bid.utility + remainder
                if total > best_utility:
                    best_utility = total
                    best_pairs = ((agent_index, task_index),) + pairs
            return best_utility, best_pairs

        total_utility, pairs = solve(0, 0)
        assignments = tuple(
            TaskAssignment(
                agents[agent_index].agent_id,
                tasks[task_index].task_id,
                bids[(agent_index, task_index)].utility,
            )
            for agent_index, task_index in pairs
        )
        assigned_tasks = {task_index for _, task_index in pairs}
        assigned_agents = {agent_index for agent_index, _ in pairs}
        return AllocationResult(
            assignments=assignments,
            unassigned_task_ids=tuple(
                task.task_id
                for task_index, task in enumerate(tasks)
                if task_index not in assigned_tasks
            ),
            idle_agent_ids=tuple(
                agent.agent_id
                for agent_index, agent in enumerate(agents)
                if agent_index not in assigned_agents
            ),
            total_utility=float(total_utility),
        )
