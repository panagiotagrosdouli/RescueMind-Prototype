import pytest

from rescuemind.models import Hypothesis, Pose2D
from rescuemind.priority import (
    PriorityContext,
    PriorityWeights,
    ProbabilisticPriorityEngine,
)


def hypothesis(**overrides) -> Hypothesis:
    values = {
        "hypothesis_id": "H-1",
        "pose": Pose2D(0.0, 0.0),
        "score": 0.75,
        "uncertainty": 0.25,
        "urgency": 0.7,
        "accessibility": 0.8,
        "hazard": 0.2,
    }
    values.update(overrides)
    return Hypothesis(**values)


def test_higher_presence_increases_priority() -> None:
    engine = ProbabilisticPriorityEngine()
    context = PriorityContext(travel_time_seconds=30.0)
    low = engine.score(hypothesis(score=0.3), context)
    high = engine.score(hypothesis(score=0.9), context)
    assert high.score > low.score


def test_higher_hazard_does_not_increase_priority() -> None:
    engine = ProbabilisticPriorityEngine()
    context = PriorityContext(travel_time_seconds=30.0)
    safe = engine.score(hypothesis(hazard=0.1), context)
    dangerous = engine.score(hypothesis(hazard=0.9), context)
    assert dangerous.score < safe.score


def test_longer_travel_time_reduces_priority() -> None:
    engine = ProbabilisticPriorityEngine()
    near = engine.score(hypothesis(), PriorityContext(travel_time_seconds=10.0))
    far = engine.score(hypothesis(), PriorityContext(travel_time_seconds=600.0))
    assert far.score < near.score


def test_uncertainty_widens_interval() -> None:
    engine = ProbabilisticPriorityEngine()
    context = PriorityContext(travel_time_seconds=30.0)
    certain = engine.score(hypothesis(uncertainty=0.05), context)
    uncertain = engine.score(hypothesis(uncertainty=0.9), context)
    assert uncertain.high - uncertain.low > certain.high - certain.low


def test_information_gain_peaks_near_ambiguous_presence() -> None:
    engine = ProbabilisticPriorityEngine()
    context = PriorityContext(travel_time_seconds=30.0)
    ambiguous = engine.score(hypothesis(score=0.5, uncertainty=0.8), context)
    confident = engine.score(hypothesis(score=0.99, uncertainty=0.8), context)
    assert (
        ambiguous.decomposition["information_gain"]
        > confident.decomposition["information_gain"]
    )


def test_rank_uses_conservative_lower_bound() -> None:
    engine = ProbabilisticPriorityEngine()
    stable = hypothesis(hypothesis_id="stable", score=0.75, uncertainty=0.05)
    unstable = hypothesis(hypothesis_id="unstable", score=0.8, uncertainty=0.95)
    contexts = {
        "stable": PriorityContext(travel_time_seconds=20.0),
        "unstable": PriorityContext(travel_time_seconds=20.0),
    }
    ranked = engine.rank([unstable, stable], contexts)
    assert ranked[0].site_id == "stable"


def test_rank_requires_context_for_every_hypothesis() -> None:
    engine = ProbabilisticPriorityEngine()
    with pytest.raises(KeyError, match="missing priority context"):
        engine.rank([hypothesis()], {})


def test_negative_travel_time_is_rejected() -> None:
    engine = ProbabilisticPriorityEngine()
    with pytest.raises(ValueError, match="non-negative"):
        engine.score(hypothesis(), PriorityContext(travel_time_seconds=-1.0))


def test_invalid_weights_are_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ProbabilisticPriorityEngine(PriorityWeights(presence=-0.1))


def test_explanation_is_grounded_in_decomposition() -> None:
    engine = ProbabilisticPriorityEngine()
    estimate = engine.score(hypothesis(), PriorityContext(travel_time_seconds=30.0))
    explanation = engine.explain(estimate)
    assert explanation["decision_support_only"] is True
    assert explanation["site_id"] == "H-1"
    assert len(explanation["dominant_terms"]) == 4
