from rescuemind.models import Observation, Pose2D, Provenance
from rescuemind.temporal import AsynchronousObservationBuffer, ClockOffsetRegistry


def observation(
    observation_id: str,
    timestamp: float,
    *,
    agent_id: str = "agent-1",
    modality: str = "thermal",
    valid_for: float = 5.0,
) -> Observation:
    return Observation(
        modality=modality,
        value=0.8,
        confidence=0.9,
        reliability=0.8,
        timestamp=timestamp,
        pose=Pose2D(1.0, 1.0),
        spatial_uncertainty=0.5,
        valid_for=valid_for,
        provenance=Provenance(observation_id, agent_id, f"{agent_id}:{modality}"),
    )


def test_clock_offsets_correct_source_time() -> None:
    offsets = ClockOffsetRegistry()
    offsets.set_offset("agent-1", 1.5)
    item = observation("obs-1", 11.5)
    assert offsets.corrected_timestamp(item) == 10.0


def test_duplicate_observations_are_rejected() -> None:
    buffer = AsynchronousObservationBuffer()
    item = observation("obs-1", 1.0)
    assert buffer.add(item)
    assert not buffer.add(item)
    assert buffer.duplicates_rejected == 1
    assert len(buffer) == 1


def test_out_of_order_arrival_is_recorded_but_sorted() -> None:
    buffer = AsynchronousObservationBuffer(alignment_window=5.0)
    buffer.add(observation("newer", 4.0), arrival_time=4.0)
    buffer.add(observation("older", 2.0), arrival_time=5.0)
    aligned = buffer.aligned(4.0)
    assert buffer.out_of_order_received == 1
    assert [item.observation.provenance.observation_id for item in aligned] == [
        "older",
        "newer",
    ]


def test_stale_observations_are_not_aligned() -> None:
    buffer = AsynchronousObservationBuffer(alignment_window=3.0, stale_after=4.0)
    buffer.add(observation("stale", 0.0, valid_for=2.0))
    assert buffer.aligned(3.0) == []
    assert buffer.reject_stale(3.0) == 1
    assert len(buffer) == 0


def test_delayed_message_is_annotated() -> None:
    buffer = AsynchronousObservationBuffer(alignment_window=2.0, stale_after=10.0)
    buffer.add(observation("late", 5.0), arrival_time=8.0)
    aligned = buffer.aligned(6.0)
    assert len(aligned) == 1
    assert aligned[0].delayed
    assert aligned[0].age == 1.0


def test_nearest_supports_modality_filtering() -> None:
    buffer = AsynchronousObservationBuffer(alignment_window=4.0)
    buffer.add(observation("thermal", 5.0, modality="thermal"))
    buffer.add(observation("acoustic", 5.5, modality="acoustic"))
    nearest = buffer.nearest(5.4, modality="acoustic")
    assert nearest is not None
    assert nearest.observation.provenance.observation_id == "acoustic"
