from rescuemind.models import Hypothesis, Observation, Pose2D, Provenance
from rescuemind.spatial import MahalanobisAssociator, evaluate_associations


def observation(
    observation_id: str,
    x: float,
    y: float,
    uncertainty: float = 0.4,
    value: float = 0.9,
) -> Observation:
    return Observation(
        modality="thermal",
        value=value,
        confidence=0.9,
        reliability=0.8,
        timestamp=1.0,
        pose=Pose2D(x, y),
        spatial_uncertainty=uncertainty,
        valid_for=3.0,
        provenance=Provenance(observation_id, "uav-1", "thermal-1"),
    )


def test_mahalanobis_gate_rejects_distant_candidate() -> None:
    associator = MahalanobisAssociator(gate_threshold=2.5)
    candidate = associator.candidate(
        observation("o-1", 0.0, 0.0, uncertainty=0.2),
        Hypothesis("h-1", Pose2D(5.0, 5.0), 0.7, 0.2),
    )
    assert candidate is None


def test_covariance_changes_gating_decision() -> None:
    hypothesis = Hypothesis("h-1", Pose2D(2.0, 0.0), 0.7, 0.2)
    associator = MahalanobisAssociator(gate_threshold=2.0)
    precise = associator.candidate(observation("precise", 0.0, 0.0, 0.1), hypothesis)
    uncertain = associator.candidate(observation("uncertain", 0.0, 0.0, 1.2), hypothesis)
    assert precise is None
    assert uncertain is not None


def test_global_assignment_is_one_to_one() -> None:
    observations = [
        observation("o-left", 0.1, 0.0),
        observation("o-right", 9.8, 0.0),
    ]
    hypotheses = [
        Hypothesis("h-left", Pose2D(0.0, 0.0), 0.8, 0.3),
        Hypothesis("h-right", Pose2D(10.0, 0.0), 0.7, 0.3),
    ]
    result = MahalanobisAssociator().assign(observations, hypotheses)
    pairs = {(match.observation_id, match.hypothesis_id) for match in result.matches}
    assert pairs == {("o-left", "h-left"), ("o-right", "h-right")}
    assert not result.unmatched_observation_ids
    assert not result.unmatched_hypothesis_ids


def test_assignment_can_leave_observation_unmatched() -> None:
    observations = [observation("near", 0.1, 0.0), observation("far", 30.0, 30.0)]
    hypotheses = [Hypothesis("h-1", Pose2D(0.0, 0.0), 0.8, 0.2)]
    result = MahalanobisAssociator().assign(observations, hypotheses)
    assert tuple(match.observation_id for match in result.matches) == ("near",)
    assert result.unmatched_observation_ids == ("far",)


def test_unmatched_observation_initializes_conservative_hypothesis() -> None:
    observations = [observation("new-target", 4.0, 5.0, uncertainty=0.6)]
    result = MahalanobisAssociator().assign(observations, [])
    created = MahalanobisAssociator.initialize_unmatched(observations, result)
    assert len(created) == 1
    assert created[0].pose == Pose2D(4.0, 5.0)
    assert created[0].status == "UNCONFIRMED"
    assert created[0].supporting == ["new-target"]
    assert created[0].uncertainty >= 0.6


def test_association_metrics_report_false_missed_and_switches() -> None:
    observations = [observation("o-1", 0.0, 0.0), observation("o-2", 10.0, 0.0)]
    hypotheses = [
        Hypothesis("h-1", Pose2D(0.0, 0.0), 0.8, 0.2),
        Hypothesis("h-2", Pose2D(10.0, 0.0), 0.8, 0.2),
    ]
    result = MahalanobisAssociator().assign(observations, hypotheses)
    metrics = evaluate_associations(
        result,
        {"o-1": "h-2", "o-2": "h-2", "missing": "h-3"},
        previous_by_observation={"o-1": "h-2", "o-2": "h-1"},
    )
    assert metrics.correct == 1
    assert metrics.false_associations == 1
    assert metrics.missed_associations == 1
    assert metrics.id_switches == 1
    assert metrics.accuracy == 1 / 3


def test_large_exact_assignment_is_rejected_explicitly() -> None:
    hypotheses = [Hypothesis(f"h-{index}", Pose2D(index, 0.0), 0.5, 0.2) for index in range(19)]
    associator = MahalanobisAssociator()
    try:
        associator.assign([], hypotheses)
    except ValueError as error:
        assert "at most 18" in str(error)
    else:
        raise AssertionError("expected explicit complexity guard")
