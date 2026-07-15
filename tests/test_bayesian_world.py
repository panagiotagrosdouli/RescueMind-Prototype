import pytest

from rescuemind.bayesian_world import BayesianEvidence, BayesianWorldModel, SurvivorBelief


def evidence(
    evidence_id: str,
    *,
    supports: bool,
    reliability: float = 1.0,
    timestamp: float = 1.0,
    hypothesis_id: str = "h-1",
    modality: str = "thermal",
) -> BayesianEvidence:
    return BayesianEvidence(
        evidence_id=evidence_id,
        hypothesis_id=hypothesis_id,
        supports_presence=supports,
        reliability=reliability,
        timestamp=timestamp,
        modality=modality,
    )


def test_supporting_evidence_increases_probability() -> None:
    model = BayesianWorldModel()
    updated = model.update(evidence("e-1", supports=True, reliability=0.8))
    assert updated.probability > 0.5
    assert updated.alpha == pytest.approx(1.8)


def test_contradictory_evidence_decreases_probability() -> None:
    model = BayesianWorldModel()
    updated = model.update(evidence("e-1", supports=False, reliability=0.8))
    assert updated.probability < 0.5
    assert updated.beta == pytest.approx(1.8)


def test_reliability_controls_evidence_weight() -> None:
    low = BayesianWorldModel().update(evidence("low", supports=True, reliability=0.2))
    high = BayesianWorldModel().update(evidence("high", supports=True, reliability=0.9))
    assert high.probability > low.probability


def test_duplicate_evidence_is_rejected() -> None:
    model = BayesianWorldModel()
    model.update(evidence("e-1", supports=True))
    with pytest.raises(ValueError, match="duplicate"):
        model.update(evidence("e-1", supports=True, timestamp=2.0))


def test_out_of_order_evidence_is_rejected() -> None:
    model = BayesianWorldModel()
    model.update(evidence("e-1", supports=True, timestamp=2.0))
    with pytest.raises(ValueError, match="monotonic"):
        model.update(evidence("e-2", supports=True, timestamp=1.0))


def test_decay_moves_probability_toward_prior() -> None:
    model = BayesianWorldModel(decay_half_life=10.0)
    model.update(evidence("e-1", supports=True, reliability=1.0, timestamp=0.0))
    initial = model.get("h-1")
    decayed = model.decayed("h-1", 10.0)
    assert 0.5 < decayed.probability < initial.probability
    assert decayed.alpha == pytest.approx(1.5)


def test_credible_interval_is_bounded() -> None:
    interval = SurvivorBelief("h-1", alpha=2.0, beta=3.0).interval()
    assert 0.0 <= interval.lower <= interval.upper <= 1.0


def test_uncertain_belief_requires_reobservation() -> None:
    model = BayesianWorldModel(uncertainty_threshold=0.3, stale_after=100.0)
    decision = model.reobservation_decision("h-1", now=0.0)
    assert decision.required
    assert decision.reason == "credible interval too wide"


def test_stale_belief_requires_reobservation() -> None:
    model = BayesianWorldModel(stale_after=10.0)
    model.update(evidence("e-1", supports=True, timestamp=1.0))
    decision = model.reobservation_decision("h-1", now=11.0)
    assert decision.required
    assert decision.reason == "stale belief"


def test_ranked_orders_by_decayed_probability() -> None:
    model = BayesianWorldModel()
    model.update(evidence("e-1", supports=True, hypothesis_id="high"))
    model.update(evidence("e-2", supports=False, hypothesis_id="low"))
    ranked = model.ranked(now=1.0)
    assert [belief.hypothesis_id for belief in ranked] == ["high", "low"]


def test_modalities_and_provenance_are_preserved() -> None:
    model = BayesianWorldModel()
    model.update(evidence("e-1", supports=True, modality="thermal", timestamp=1.0))
    updated = model.update(
        evidence("e-2", supports=True, modality="acoustic", timestamp=2.0)
    )
    assert updated.evidence_ids == ("e-1", "e-2")
    assert updated.modalities == frozenset({"thermal", "acoustic"})
