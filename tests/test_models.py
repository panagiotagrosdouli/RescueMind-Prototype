"""Tests for the initial RescueMind domain models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from rescuemind.models import Observation, RescuePriorityEstimate, SensorModality


def test_observation_accepts_timezone_aware_timestamp() -> None:
    observation = Observation(
        observation_id="obs-001",
        source_id="thermal-camera-01",
        modality=SensorModality.THERMAL,
        timestamp=datetime.now(timezone.utc),
        frame_id="map",
        confidence=0.82,
        payload={"maximum_temperature_c": 36.7},
    )

    assert observation.confidence == pytest.approx(0.82)


def test_observation_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        Observation(
            observation_id="obs-002",
            source_id="microphone-array-01",
            modality=SensorModality.ACOUSTIC,
            timestamp=datetime.now(),
            frame_id="robot_base",
            confidence=0.60,
            payload={"event": "human_voice"},
        )


def test_rescue_priority_estimate_is_bounded() -> None:
    estimate = RescuePriorityEstimate(
        location_id="sector-a3",
        human_presence_probability=0.88,
        survivability_probability=0.72,
        accessibility=0.55,
        safety=0.63,
        urgency=0.91,
        uncertainty=0.24,
        score=0.74,
        supporting_observation_ids=("obs-001", "obs-003"),
    )

    assert 0.0 <= estimate.score <= 1.0
