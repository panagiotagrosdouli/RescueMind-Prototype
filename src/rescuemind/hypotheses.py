"""Spatial association and lifecycle management for survivor hypotheses."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import exp, hypot

from .models import Hypothesis, Observation, Pose2D


class HypothesisStatus(StrEnum):
    UNCONFIRMED = "UNCONFIRMED"
    POSSIBLE = "POSSIBLE"
    PROBABLE = "PROBABLE"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    REQUIRES_REOBSERVATION = "REQUIRES_REOBSERVATION"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class AssociationResult:
    hypothesis_id: str | None
    distance: float
    association_score: float
    ambiguous: bool


class SpatialAssociator:
    """Associate observations with hypotheses using distance and uncertainty gates."""

    def __init__(self, gate_scale: float = 2.5, ambiguity_margin: float = 0.08):
        self.gate_scale = gate_scale
        self.ambiguity_margin = ambiguity_margin

    def associate(
        self, observation: Observation, hypotheses: list[Hypothesis]
    ) -> AssociationResult:
        candidates: list[tuple[float, Hypothesis]] = []
        for hypothesis in hypotheses:
            distance = hypot(
                observation.pose.x - hypothesis.pose.x,
                observation.pose.y - hypothesis.pose.y,
            )
            gate = self.gate_scale * max(
                0.5,
                observation.spatial_uncertainty + hypothesis.uncertainty,
            )
            if distance <= gate:
                score = exp(-0.5 * (distance / max(gate, 1e-9)) ** 2)
                candidates.append((score, hypothesis))

        if not candidates:
            return AssociationResult(None, float("inf"), 0.0, False)

        candidates.sort(key=lambda item: item[0], reverse=True)
        best_score, best = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else 0.0
        distance = hypot(
            observation.pose.x - best.pose.x,
            observation.pose.y - best.pose.y,
        )
        return AssociationResult(
            best.hypothesis_id,
            distance,
            best_score,
            len(candidates) > 1 and best_score - second_score < self.ambiguity_margin,
        )


class HypothesisManager:
    """Maintain survivor hypotheses without hiding uncertainty or contradictions."""

    def __init__(self, retirement_age: float = 8.0):
        self.retirement_age = retirement_age
        self._last_update: dict[str, float] = {}

    @staticmethod
    def classify(score: float, uncertainty: float, supporting: int, contradicting: int) -> str:
        if contradicting >= 3 and score < 0.35:
            return HypothesisStatus.REJECTED
        if uncertainty > 0.65:
            return HypothesisStatus.REQUIRES_REOBSERVATION
        if score >= 0.80 and supporting >= 2:
            return HypothesisStatus.HIGH_PRIORITY
        if score >= 0.65:
            return HypothesisStatus.PROBABLE
        if score >= 0.45:
            return HypothesisStatus.POSSIBLE
        return HypothesisStatus.UNCONFIRMED

    def update(
        self,
        hypothesis: Hypothesis,
        observation: Observation,
        now: float,
    ) -> Hypothesis:
        positive = observation.value >= 0.5
        supporting = list(hypothesis.supporting)
        contradicting = list(hypothesis.contradicting)
        target = supporting if positive else contradicting
        if observation.provenance.observation_id not in target:
            target.append(observation.provenance.observation_id)

        evidence = observation.value if positive else 1.0 - observation.value
        reliability = observation.reliability * observation.confidence
        signed = evidence if positive else -evidence
        score = min(1.0, max(0.0, hypothesis.score + 0.18 * reliability * signed))
        uncertainty = min(
            1.0,
            max(0.0, hypothesis.uncertainty - 0.12 * reliability + 0.08 * (not positive)),
        )
        pose_weight = max(0.05, reliability / max(observation.spatial_uncertainty, 0.1))
        old_weight = max(0.05, 1.0 / max(hypothesis.uncertainty, 0.1))
        pose = Pose2D(
            (hypothesis.pose.x * old_weight + observation.pose.x * pose_weight)
            / (old_weight + pose_weight),
            (hypothesis.pose.y * old_weight + observation.pose.y * pose_weight)
            / (old_weight + pose_weight),
            hypothesis.pose.yaw,
        )
        status = self.classify(score, uncertainty, len(supporting), len(contradicting))
        self._last_update[hypothesis.hypothesis_id] = now
        return replace(
            hypothesis,
            pose=pose,
            score=score,
            uncertainty=uncertainty,
            supporting=supporting,
            contradicting=contradicting,
            status=str(status),
        )

    def retire_stale(self, hypotheses: list[Hypothesis], now: float) -> list[Hypothesis]:
        updated: list[Hypothesis] = []
        for hypothesis in hypotheses:
            age = now - self._last_update.get(hypothesis.hypothesis_id, now)
            if age > self.retirement_age and hypothesis.status not in {
                HypothesisStatus.REJECTED,
                HypothesisStatus.RESOLVED,
            }:
                updated.append(
                    replace(
                        hypothesis,
                        status=str(HypothesisStatus.REQUIRES_REOBSERVATION),
                        uncertainty=min(1.0, hypothesis.uncertainty + 0.2),
                    )
                )
            else:
                updated.append(hypothesis)
        return updated

    @staticmethod
    def merge(first: Hypothesis, second: Hypothesis) -> Hypothesis:
        total_confidence = max(1e-9, (1.0 - first.uncertainty) + (1.0 - second.uncertainty))
        first_weight = (1.0 - first.uncertainty) / total_confidence
        second_weight = (1.0 - second.uncertainty) / total_confidence
        score = first.score * first_weight + second.score * second_weight
        uncertainty = min(first.uncertainty, second.uncertainty)
        supporting = list(dict.fromkeys(first.supporting + second.supporting))
        contradicting = list(dict.fromkeys(first.contradicting + second.contradicting))
        return Hypothesis(
            hypothesis_id=first.hypothesis_id,
            pose=Pose2D(
                first.pose.x * first_weight + second.pose.x * second_weight,
                first.pose.y * first_weight + second.pose.y * second_weight,
            ),
            score=score,
            uncertainty=uncertainty,
            supporting=supporting,
            contradicting=contradicting,
            status=str(
                HypothesisManager.classify(
                    score, uncertainty, len(supporting), len(contradicting)
                )
            ),
            urgency=max(first.urgency, second.urgency),
            accessibility=min(first.accessibility, second.accessibility),
            hazard=max(first.hazard, second.hazard),
        )
