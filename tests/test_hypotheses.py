from rescuemind.hypotheses import (
    HypothesisManager,
    HypothesisStatus,
    SpatialAssociator,
)
from rescuemind.models import Hypothesis, Observation, Pose2D, Provenance


def make_observation(value: float, x: float = 1.0, y: float = 1.0) -> Observation:
    return Observation(
        modality="thermal",
        value=value,
        confidence=0.9,
        reliability=0.8,
        timestamp=1.0,
        pose=Pose2D(x, y),
        spatial_uncertainty=0.5,
        valid_for=3.0,
        provenance=Provenance(f"obs-{value}-{x}-{y}", "uav-1", "thermal-1"),
    )


def test_spatial_association_selects_nearest_valid_hypothesis() -> None:
    hypotheses = [
        Hypothesis("near", Pose2D(1.2, 1.1), 0.5, 0.3),
        Hypothesis("far", Pose2D(8.0, 8.0), 0.7, 0.2),
    ]
    result = SpatialAssociator().associate(make_observation(0.8), hypotheses)
    assert result.hypothesis_id == "near"
    assert not result.ambiguous
    assert result.association_score > 0.0


def test_positive_evidence_advances_hypothesis_lifecycle() -> None:
    manager = HypothesisManager()
    hypothesis = Hypothesis("S-1", Pose2D(1.0, 1.0), 0.64, 0.25, supporting=["old"])
    updated = manager.update(hypothesis, make_observation(0.95), now=1.0)
    assert updated.score > hypothesis.score
    assert len(updated.supporting) == 2
    assert updated.status in {
        str(HypothesisStatus.PROBABLE),
        str(HypothesisStatus.HIGH_PRIORITY),
    }


def test_contradicting_evidence_is_traceable() -> None:
    manager = HypothesisManager()
    hypothesis = Hypothesis("S-2", Pose2D(1.0, 1.0), 0.5, 0.4)
    updated = manager.update(hypothesis, make_observation(0.05), now=1.0)
    assert updated.score < hypothesis.score
    assert updated.contradicting
    assert updated.uncertainty >= hypothesis.uncertainty


def test_stale_hypothesis_requires_reobservation() -> None:
    manager = HypothesisManager(retirement_age=2.0)
    hypothesis = Hypothesis("S-3", Pose2D(1.0, 1.0), 0.7, 0.2)
    manager.update(hypothesis, make_observation(0.8), now=1.0)
    retired = manager.retire_stale([hypothesis], now=4.0)[0]
    assert retired.status == str(HypothesisStatus.REQUIRES_REOBSERVATION)
    assert retired.uncertainty > hypothesis.uncertainty


def test_merge_deduplicates_provenance() -> None:
    first = Hypothesis("S-4", Pose2D(1.0, 1.0), 0.7, 0.3, supporting=["a", "b"])
    second = Hypothesis("S-5", Pose2D(1.5, 1.5), 0.8, 0.2, supporting=["b", "c"])
    merged = HypothesisManager.merge(first, second)
    assert merged.hypothesis_id == "S-4"
    assert merged.supporting == ["a", "b", "c"]
    assert 0.7 <= merged.score <= 0.8
