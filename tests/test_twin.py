from __future__ import annotations

import pytest

from rescuemind.models import Hypothesis, Pose2D
from rescuemind.twin import LivingDisasterTwin


def hypothesis(hypothesis_id: str = "h-1") -> Hypothesis:
    return Hypothesis(
        hypothesis_id=hypothesis_id,
        pose=Pose2D(2.0, 3.0),
        score=0.8,
        uncertainty=0.25,
        supporting=["o-1", "o-1", "o-2"],
        contradicting=["o-3"],
        status="PROBABLE",
    )


def test_update_creates_versioned_snapshot_and_event() -> None:
    twin = LivingDisasterTwin()
    snapshot = twin.update(hypothesis(), 10.0)
    assert snapshot.revision == 1
    assert snapshot.source_ids == ("o-1", "o-2", "o-3")
    assert twin.events[0].event_type == "created"


def test_second_update_is_auditable() -> None:
    twin = LivingDisasterTwin()
    item = hypothesis()
    twin.update(item, 10.0)
    item.score = 0.9
    snapshot = twin.update(item, 20.0)
    assert snapshot.revision == 2
    assert twin.events[-1].event_type == "updated"


def test_rejects_out_of_order_updates() -> None:
    twin = LivingDisasterTwin()
    twin.update(hypothesis(), 10.0)
    with pytest.raises(ValueError, match="monotonic"):
        twin.update(hypothesis(), 9.0)


def test_freshness_halves_at_half_life() -> None:
    twin = LivingDisasterTwin(freshness_half_life=20.0)
    twin.update(hypothesis(), 10.0)
    assert twin.freshness("h-1", 30.0) == pytest.approx(0.5)


def test_view_hides_stale_by_default() -> None:
    twin = LivingDisasterTwin(stale_after=5.0)
    twin.update(hypothesis(), 0.0)
    assert twin.view(6.0) == []
    assert twin.view(6.0, include_stale=True)[0]["status"] == "STALE"


def test_resolve_preserves_provenance() -> None:
    twin = LivingDisasterTwin()
    twin.update(hypothesis(), 1.0)
    resolved = twin.resolve("h-1", 2.0)
    assert resolved.status == "RESOLVED"
    assert resolved.source_ids == ("o-1", "o-2", "o-3")
    assert twin.events[-1].event_type == "resolved"


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        LivingDisasterTwin(freshness_half_life=0.0)
    with pytest.raises(ValueError):
        LivingDisasterTwin(stale_after=0.0)


def test_negative_timestamp_is_rejected() -> None:
    twin = LivingDisasterTwin()
    with pytest.raises(ValueError):
        twin.update(hypothesis(), -1.0)
