"""Versioned, auditable living disaster twin for synthetic experiments.

The twin stores compact hypothesis snapshots with explicit freshness and provenance.
It is decision-support research software and is not an operational incident map.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp

from .models import Hypothesis, Pose2D


@dataclass(frozen=True)
class TwinSnapshot:
    hypothesis_id: str
    pose: Pose2D
    score: float
    uncertainty: float
    status: str
    updated_at: float
    revision: int
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class TwinEvent:
    revision: int
    event_type: str
    hypothesis_id: str
    timestamp: float
    details: dict[str, object] = field(default_factory=dict)


class LivingDisasterTwin:
    """Maintain versioned hypothesis state with deterministic freshness decay."""

    def __init__(self, freshness_half_life: float = 60.0, stale_after: float = 300.0):
        if freshness_half_life <= 0.0:
            raise ValueError("freshness_half_life must be positive")
        if stale_after <= 0.0:
            raise ValueError("stale_after must be positive")
        self.freshness_half_life = freshness_half_life
        self.stale_after = stale_after
        self.revision = 0
        self._snapshots: dict[str, TwinSnapshot] = {}
        self._events: list[TwinEvent] = []

    @property
    def events(self) -> tuple[TwinEvent, ...]:
        return tuple(self._events)

    def update(self, hypothesis: Hypothesis, timestamp: float) -> TwinSnapshot:
        if timestamp < 0.0:
            raise ValueError("timestamp must be non-negative")
        previous = self._snapshots.get(hypothesis.hypothesis_id)
        if previous is not None and timestamp < previous.updated_at:
            raise ValueError("twin updates must be monotonic per hypothesis")

        self.revision += 1
        source_ids = tuple(dict.fromkeys(hypothesis.supporting + hypothesis.contradicting))
        snapshot = TwinSnapshot(
            hypothesis_id=hypothesis.hypothesis_id,
            pose=Pose2D(hypothesis.pose.x, hypothesis.pose.y, hypothesis.pose.yaw),
            score=float(min(1.0, max(0.0, hypothesis.score))),
            uncertainty=float(min(1.0, max(0.0, hypothesis.uncertainty))),
            status=hypothesis.status,
            updated_at=timestamp,
            revision=self.revision,
            source_ids=source_ids,
        )
        self._snapshots[hypothesis.hypothesis_id] = snapshot
        self._events.append(
            TwinEvent(
                revision=self.revision,
                event_type="created" if previous is None else "updated",
                hypothesis_id=hypothesis.hypothesis_id,
                timestamp=timestamp,
                details={"source_count": len(source_ids)},
            )
        )
        return snapshot

    def resolve(self, hypothesis_id: str, timestamp: float) -> TwinSnapshot:
        snapshot = self._snapshots[hypothesis_id]
        self.revision += 1
        resolved = TwinSnapshot(
            hypothesis_id=snapshot.hypothesis_id,
            pose=snapshot.pose,
            score=snapshot.score,
            uncertainty=snapshot.uncertainty,
            status="RESOLVED",
            updated_at=timestamp,
            revision=self.revision,
            source_ids=snapshot.source_ids,
        )
        self._snapshots[hypothesis_id] = resolved
        self._events.append(TwinEvent(self.revision, "resolved", hypothesis_id, timestamp))
        return resolved

    def freshness(self, hypothesis_id: str, now: float) -> float:
        snapshot = self._snapshots[hypothesis_id]
        age = max(0.0, now - snapshot.updated_at)
        return float(exp(-0.6931471805599453 * age / self.freshness_half_life))

    def view(self, now: float, include_stale: bool = False) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for snapshot in self._snapshots.values():
            age = max(0.0, now - snapshot.updated_at)
            stale = age > self.stale_after
            if stale and not include_stale:
                continue
            rows.append(
                {
                    "hypothesis_id": snapshot.hypothesis_id,
                    "pose": {"x": snapshot.pose.x, "y": snapshot.pose.y, "yaw": snapshot.pose.yaw},
                    "score": snapshot.score,
                    "uncertainty": snapshot.uncertainty,
                    "status": "STALE" if stale and snapshot.status != "RESOLVED" else snapshot.status,
                    "updated_at": snapshot.updated_at,
                    "revision": snapshot.revision,
                    "freshness": self.freshness(snapshot.hypothesis_id, now),
                    "source_ids": list(snapshot.source_ids),
                }
            )
        return sorted(rows, key=lambda row: (row["status"] == "RESOLVED", -float(row["freshness"])))

    def snapshot(self, hypothesis_id: str) -> TwinSnapshot:
        return self._snapshots[hypothesis_id]
