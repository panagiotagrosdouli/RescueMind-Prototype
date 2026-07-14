"""Typed domain models shared across RescueMind components."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, Field, field_validator


class SensorModality(StrEnum):
    """Supported high-level sensing modalities."""

    RGB = "rgb"
    THERMAL = "thermal"
    DEPTH = "depth"
    ACOUSTIC = "acoustic"
    RADAR = "radar"
    CO2 = "co2"
    VIBRATION = "vibration"
    ROBOT_STATE = "robot_state"


class Observation(BaseModel):
    """A timestamped sensor observation with explicit provenance and confidence."""

    observation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    modality: SensorModality
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    frame_id: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    payload: dict[str, float | int | str | bool]

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject ambiguous timestamps because temporal alignment is safety-critical."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class RescuePriorityEstimate(BaseModel):
    """Interpretable priority estimate for a candidate intervention location."""

    location_id: str = Field(min_length=1)
    human_presence_probability: float = Field(ge=0.0, le=1.0)
    survivability_probability: float = Field(ge=0.0, le=1.0)
    accessibility: float = Field(ge=0.0, le=1.0)
    safety: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)
    supporting_observation_ids: tuple[str, ...] = ()

    @field_validator("score")
    @classmethod
    def require_finite_score(cls, value: float) -> float:
        """Prevent invalid numerical values from entering ranking logic."""
        if not isfinite(value):
            raise ValueError("score must be finite")
        return value
