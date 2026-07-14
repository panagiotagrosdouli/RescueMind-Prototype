"""Validation tests for implemented RescueMind domain models."""

from rescuemind import Hypothesis, Observation, Pose2D, PriorityModel, Provenance


def test_observation_preserves_provenance_and_validity() -> None:
    provenance = Provenance("obs-001", "uav-1", "uav-1:thermal")
    observation = Observation("thermal", 0.82, 0.9, 0.8, 1.0, Pose2D(2, 3), 1.2, 3.0, provenance)
    assert observation.provenance.observation_id == "obs-001"
    assert not observation.stale(3.0)
    assert observation.stale(5.0)


def test_priority_estimate_exposes_bounded_interval_and_decomposition() -> None:
    hypothesis = Hypothesis("site-a3", Pose2D(4, 5), 0.78, 0.24, urgency=0.91, accessibility=0.55, hazard=0.2)
    estimate = PriorityModel().score(hypothesis, travel_time=12.0)
    assert estimate.low < estimate.score < estimate.high
    assert abs(sum(estimate.decomposition.values()) - estimate.score) < 1e-9
