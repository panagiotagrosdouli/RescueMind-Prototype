"""Temporal alignment for asynchronous, delayed, and out-of-order observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import Observation


@dataclass(frozen=True)
class AlignedObservation:
    """Observation annotated with corrected time and alignment metadata."""

    observation: Observation
    corrected_timestamp: float
    age: float
    delayed: bool
    out_of_order: bool


class ClockOffsetRegistry:
    """Maintain estimated source-clock offsets in seconds."""

    def __init__(self) -> None:
        self._offsets: dict[str, float] = {}

    def set_offset(self, source_id: str, offset: float) -> None:
        self._offsets[source_id] = float(offset)

    def get_offset(self, source_id: str) -> float:
        return self._offsets.get(source_id, 0.0)

    def corrected_timestamp(self, observation: Observation) -> float:
        source_id = observation.provenance.agent_id
        return observation.timestamp - self.get_offset(source_id)


class AsynchronousObservationBuffer:
    """Buffer observations while preserving delay and ordering information.

    The buffer never mutates observations and never treats stale data as current.
    Duplicate observation IDs are rejected to prevent repeated reports from being
    fused more than once.
    """

    def __init__(
        self,
        alignment_window: float = 2.0,
        stale_after: float = 5.0,
        clock_offsets: ClockOffsetRegistry | None = None,
    ) -> None:
        if alignment_window <= 0.0:
            raise ValueError("alignment_window must be positive")
        if stale_after <= 0.0:
            raise ValueError("stale_after must be positive")
        self.alignment_window = float(alignment_window)
        self.stale_after = float(stale_after)
        self.clock_offsets = clock_offsets or ClockOffsetRegistry()
        self._items: dict[str, Observation] = {}
        self._arrival_times: dict[str, float] = {}
        self._latest_corrected_timestamp = float("-inf")
        self.duplicates_rejected = 0
        self.out_of_order_received = 0

    def add(self, observation: Observation, arrival_time: float | None = None) -> bool:
        observation_id = observation.provenance.observation_id
        if observation_id in self._items:
            self.duplicates_rejected += 1
            return False

        corrected = self.clock_offsets.corrected_timestamp(observation)
        if corrected < self._latest_corrected_timestamp:
            self.out_of_order_received += 1
        self._latest_corrected_timestamp = max(self._latest_corrected_timestamp, corrected)
        self._items[observation_id] = observation
        self._arrival_times[observation_id] = (
            corrected if arrival_time is None else float(arrival_time)
        )
        return True

    def extend(
        self,
        observations: Iterable[Observation],
        arrival_time: float | None = None,
    ) -> int:
        return sum(self.add(observation, arrival_time) for observation in observations)

    def aligned(self, reference_time: float) -> list[AlignedObservation]:
        reference_time = float(reference_time)
        aligned: list[AlignedObservation] = []
        ordered = sorted(
            self._items.values(),
            key=self.clock_offsets.corrected_timestamp,
        )
        previous_timestamp = float("-inf")
        for observation in ordered:
            corrected = self.clock_offsets.corrected_timestamp(observation)
            age = reference_time - corrected
            if age < -self.alignment_window:
                continue
            if age > min(self.stale_after, observation.valid_for):
                continue
            if abs(age) > self.alignment_window:
                continue

            observation_id = observation.provenance.observation_id
            arrival_time = self._arrival_times[observation_id]
            aligned.append(
                AlignedObservation(
                    observation=observation,
                    corrected_timestamp=corrected,
                    age=age,
                    delayed=arrival_time - corrected > self.alignment_window,
                    out_of_order=corrected < previous_timestamp,
                )
            )
            previous_timestamp = max(previous_timestamp, corrected)
        return aligned

    def reject_stale(self, reference_time: float) -> int:
        stale_ids = [
            observation.provenance.observation_id
            for observation in self._items.values()
            if reference_time - self.clock_offsets.corrected_timestamp(observation)
            > min(self.stale_after, observation.valid_for)
        ]
        for observation_id in stale_ids:
            self._items.pop(observation_id, None)
            self._arrival_times.pop(observation_id, None)
        return len(stale_ids)

    def nearest(
        self,
        target_time: float,
        modality: str | None = None,
    ) -> AlignedObservation | None:
        candidates = self.aligned(target_time)
        if modality is not None:
            candidates = [
                item for item in candidates if item.observation.modality == modality
            ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: abs(item.corrected_timestamp - target_time))

    def __len__(self) -> int:
        return len(self._items)
