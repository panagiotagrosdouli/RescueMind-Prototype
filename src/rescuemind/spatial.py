"""Covariance-aware spatial data association for survivor hypotheses.

The module intentionally uses only NumPy and the Python standard library so the
research prototype remains CPU-only and reproducible in minimal environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import exp, hypot

import numpy as np

from .models import Hypothesis, Observation, Pose2D


@dataclass(frozen=True)
class SpatialMatch:
    """A gated observation-to-hypothesis association candidate."""

    observation_id: str
    hypothesis_id: str
    mahalanobis_distance: float
    euclidean_distance: float
    likelihood: float


@dataclass(frozen=True)
class AssignmentResult:
    """Globally consistent one-to-one association result."""

    matches: tuple[SpatialMatch, ...]
    unmatched_observation_ids: tuple[str, ...]
    unmatched_hypothesis_ids: tuple[str, ...]
    total_cost: float


@dataclass(frozen=True)
class AssociationMetrics:
    """Evaluation counters for labelled synthetic association experiments."""

    correct: int
    false_associations: int
    missed_associations: int
    id_switches: int

    @property
    def accuracy(self) -> float:
        denominator = self.correct + self.false_associations + self.missed_associations
        return self.correct / denominator if denominator else 1.0


class MahalanobisAssociator:
    """Build and solve covariance-aware one-to-one spatial associations.

    Spatial uncertainty in the current domain model is scalar. It is interpreted
    as an isotropic standard deviation and combined in quadrature with the
    hypothesis uncertainty. This assumption is explicit and can later be
    replaced by full covariance matrices without changing the assignment API.
    """

    def __init__(self, gate_threshold: float = 3.0, missed_cost: float = 3.5):
        if gate_threshold <= 0.0:
            raise ValueError("gate_threshold must be positive")
        if missed_cost <= 0.0:
            raise ValueError("missed_cost must be positive")
        self.gate_threshold = gate_threshold
        self.missed_cost = missed_cost

    @staticmethod
    def _combined_variance(observation: Observation, hypothesis: Hypothesis) -> float:
        observation_sigma = max(0.05, observation.spatial_uncertainty)
        hypothesis_sigma = max(0.05, hypothesis.uncertainty)
        return observation_sigma**2 + hypothesis_sigma**2

    def candidate(self, observation: Observation, hypothesis: Hypothesis) -> SpatialMatch | None:
        dx = observation.pose.x - hypothesis.pose.x
        dy = observation.pose.y - hypothesis.pose.y
        euclidean = hypot(dx, dy)
        variance = self._combined_variance(observation, hypothesis)
        mahalanobis = float(np.sqrt((dx * dx + dy * dy) / variance))
        if mahalanobis > self.gate_threshold:
            return None
        likelihood = exp(-0.5 * mahalanobis**2)
        return SpatialMatch(
            observation.provenance.observation_id,
            hypothesis.hypothesis_id,
            mahalanobis,
            euclidean,
            likelihood,
        )

    def candidates(
        self, observations: list[Observation], hypotheses: list[Hypothesis]
    ) -> tuple[SpatialMatch, ...]:
        matches = [
            match
            for observation in observations
            for hypothesis in hypotheses
            if (match := self.candidate(observation, hypothesis)) is not None
        ]
        return tuple(sorted(matches, key=lambda item: item.mahalanobis_distance))

    def assign(
        self, observations: list[Observation], hypotheses: list[Hypothesis]
    ) -> AssignmentResult:
        """Find the minimum-cost one-to-one assignment with optional misses.

        A dynamic-programming bitmask solver is used instead of SciPy. It is
        exact for the small candidate sets expected in the current prototype.
        The method raises for large hypothesis sets rather than silently causing
        exponential runtimes.
        """

        if len(hypotheses) > 18:
            raise ValueError("exact assignment supports at most 18 hypotheses")

        candidate_map: dict[tuple[int, int], SpatialMatch] = {}
        for observation_index, observation in enumerate(observations):
            for hypothesis_index, hypothesis in enumerate(hypotheses):
                match = self.candidate(observation, hypothesis)
                if match is not None:
                    candidate_map[(observation_index, hypothesis_index)] = match

        @lru_cache(maxsize=None)
        def solve(observation_index: int, used_mask: int) -> tuple[float, tuple[tuple[int, int], ...]]:
            if observation_index == len(observations):
                return 0.0, ()

            best_cost, best_pairs = solve(observation_index + 1, used_mask)
            best_cost += self.missed_cost

            for hypothesis_index in range(len(hypotheses)):
                if used_mask & (1 << hypothesis_index):
                    continue
                match = candidate_map.get((observation_index, hypothesis_index))
                if match is None:
                    continue
                remainder_cost, remainder_pairs = solve(
                    observation_index + 1,
                    used_mask | (1 << hypothesis_index),
                )
                total = match.mahalanobis_distance + remainder_cost
                if total < best_cost:
                    best_cost = total
                    best_pairs = ((observation_index, hypothesis_index),) + remainder_pairs
            return best_cost, best_pairs

        total_cost, index_pairs = solve(0, 0)
        selected = tuple(candidate_map[pair] for pair in index_pairs)
        matched_observations = {item[0] for item in index_pairs}
        matched_hypotheses = {item[1] for item in index_pairs}
        return AssignmentResult(
            selected,
            tuple(
                observation.provenance.observation_id
                for index, observation in enumerate(observations)
                if index not in matched_observations
            ),
            tuple(
                hypothesis.hypothesis_id
                for index, hypothesis in enumerate(hypotheses)
                if index not in matched_hypotheses
            ),
            float(total_cost),
        )

    @staticmethod
    def initialize_unmatched(
        observations: list[Observation], result: AssignmentResult, prefix: str = "H"
    ) -> list[Hypothesis]:
        """Create conservative hypotheses for unmatched observations."""

        unmatched = set(result.unmatched_observation_ids)
        created: list[Hypothesis] = []
        for index, observation in enumerate(observations, start=1):
            observation_id = observation.provenance.observation_id
            if observation_id not in unmatched:
                continue
            created.append(
                Hypothesis(
                    hypothesis_id=f"{prefix}-{observation_id[:8]}-{index}",
                    pose=Pose2D(observation.pose.x, observation.pose.y, observation.pose.yaw),
                    score=float(np.clip(observation.value * observation.reliability, 0.0, 1.0)),
                    uncertainty=float(
                        np.clip(
                            max(observation.spatial_uncertainty, 1.0 - observation.confidence),
                            0.0,
                            1.0,
                        )
                    ),
                    supporting=[observation_id] if observation.value >= 0.5 else [],
                    contradicting=[observation_id] if observation.value < 0.5 else [],
                    status="UNCONFIRMED",
                )
            )
        return created


def evaluate_associations(
    result: AssignmentResult,
    expected_by_observation: dict[str, str],
    previous_by_observation: dict[str, str] | None = None,
) -> AssociationMetrics:
    """Evaluate an assignment against labelled synthetic correspondences.

    An ID switch is counted only when the current association is correct and its
    hypothesis identity differs from the previous association. Incorrect current
    assignments remain false associations and are not double-counted as switches.
    """

    observed = {match.observation_id: match.hypothesis_id for match in result.matches}
    correct = 0
    false = 0
    missed = 0
    switches = 0
    previous = previous_by_observation or {}

    for observation_id, expected_hypothesis in expected_by_observation.items():
        actual = observed.get(observation_id)
        if actual is None:
            missed += 1
        elif actual == expected_hypothesis:
            correct += 1
            if observation_id in previous and actual != previous[observation_id]:
                switches += 1
        else:
            false += 1

    return AssociationMetrics(correct, false, missed, switches)
