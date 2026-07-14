"""Probabilistic and explainable rescue-priority estimation.

This module provides decision-support scores for synthetic research scenarios.
It does not make autonomous emergency-response decisions and has not been
validated on real incidents, physical robots, or clinical outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log2

import numpy as np

from .models import Hypothesis, PriorityEstimate


@dataclass(frozen=True)
class PriorityContext:
    """Operational context used to evaluate one survivor hypothesis."""

    travel_time_seconds: float
    responder_risk: float = 0.0
    communication_quality: float = 1.0
    verification_cost: float = 0.0


@dataclass(frozen=True)
class PriorityWeights:
    """Normalized coefficients for the utility decomposition."""

    presence: float = 0.30
    urgency: float = 0.20
    survivability: float = 0.15
    accessibility: float = 0.12
    information_gain: float = 0.10
    travel_penalty: float = 0.05
    hazard_penalty: float = 0.04
    responder_risk_penalty: float = 0.02
    communication_penalty: float = 0.01
    verification_penalty: float = 0.01

    def as_dict(self) -> dict[str, float]:
        values = {
            "presence": self.presence,
            "urgency": self.urgency,
            "survivability": self.survivability,
            "accessibility": self.accessibility,
            "information_gain": self.information_gain,
            "travel_penalty": self.travel_penalty,
            "hazard_penalty": self.hazard_penalty,
            "responder_risk_penalty": self.responder_risk_penalty,
            "communication_penalty": self.communication_penalty,
            "verification_penalty": self.verification_penalty,
        }
        if any(value < 0.0 for value in values.values()):
            raise ValueError("priority weights must be non-negative")
        total = sum(values.values())
        if total <= 0.0:
            raise ValueError("at least one priority weight must be positive")
        return {key: value / total for key, value in values.items()}


class ProbabilisticPriorityEngine:
    """Compute bounded, decomposable rescue-priority utility estimates."""

    def __init__(self, weights: PriorityWeights | None = None):
        self.weights = (weights or PriorityWeights()).as_dict()

    @staticmethod
    def _clip(value: float) -> float:
        return float(np.clip(value, 0.0, 1.0))

    @staticmethod
    def binary_entropy(probability: float) -> float:
        """Return normalized binary entropy in [0, 1]."""

        p = float(np.clip(probability, 1e-12, 1.0 - 1e-12))
        return float(-(p * log2(p) + (1.0 - p) * log2(1.0 - p)))

    def score(self, hypothesis: Hypothesis, context: PriorityContext) -> PriorityEstimate:
        """Estimate expected utility and a conservative uncertainty interval."""

        if context.travel_time_seconds < 0.0:
            raise ValueError("travel_time_seconds must be non-negative")

        presence = self._clip(hypothesis.score)
        uncertainty = self._clip(hypothesis.uncertainty)
        urgency = self._clip(hypothesis.urgency)
        hazard = self._clip(hypothesis.hazard)
        accessibility = self._clip(hypothesis.accessibility)
        responder_risk = self._clip(context.responder_risk)
        communication_quality = self._clip(context.communication_quality)
        verification_cost = self._clip(context.verification_cost)

        survivability = self._clip((1.0 - 0.7 * hazard) * (0.55 + 0.45 * urgency))
        information_gain = self.binary_entropy(presence) * uncertainty
        travel_penalty = self._clip(context.travel_time_seconds / 600.0)

        raw_terms = {
            "presence": presence,
            "urgency": urgency,
            "survivability": survivability,
            "accessibility": accessibility,
            "information_gain": information_gain,
            "travel_penalty": -travel_penalty,
            "hazard_penalty": -hazard,
            "responder_risk_penalty": -responder_risk,
            "communication_penalty": -(1.0 - communication_quality),
            "verification_penalty": -verification_cost,
        }
        decomposition = {
            key: self.weights[key] * raw_terms[key] for key in self.weights
        }
        utility = float(np.clip(sum(decomposition.values()), -1.0, 1.0))

        epistemic_width = 0.08 + 0.28 * uncertainty
        communication_width = 0.08 * (1.0 - communication_quality)
        hazard_width = 0.05 * hazard
        interval = min(0.5, epistemic_width + communication_width + hazard_width)

        return PriorityEstimate(
            site_id=hypothesis.hypothesis_id,
            score=utility,
            low=float(max(-1.0, utility - interval)),
            high=float(min(1.0, utility + interval)),
            decomposition=decomposition,
            rank_instability=float(min(1.0, 2.0 * interval)),
        )

    def rank(
        self,
        hypotheses: list[Hypothesis],
        contexts: dict[str, PriorityContext],
    ) -> list[PriorityEstimate]:
        """Rank hypotheses by conservative lower-bound utility."""

        estimates = []
        for hypothesis in hypotheses:
            try:
                context = contexts[hypothesis.hypothesis_id]
            except KeyError as exc:
                raise KeyError(
                    f"missing priority context for {hypothesis.hypothesis_id}"
                ) from exc
            estimates.append(self.score(hypothesis, context))
        return sorted(estimates, key=lambda item: (item.low, item.score), reverse=True)

    @staticmethod
    def explain(estimate: PriorityEstimate) -> dict[str, object]:
        """Return a grounded decomposition without generated causal claims."""

        dominant = sorted(
            estimate.decomposition.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:4]
        return {
            "site_id": estimate.site_id,
            "decision_support_only": True,
            "score": estimate.score,
            "interval": [estimate.low, estimate.high],
            "rank_instability": estimate.rank_instability,
            "dominant_terms": [
                {"term": term, "contribution": contribution}
                for term, contribution in dominant
            ],
        }
