from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class ReliabilityState(str, Enum):
    RELIABLE='RELIABLE'; DEGRADED='DEGRADED'; UNCERTAIN='UNCERTAIN'; FAILED='FAILED'; STALE='STALE'

@dataclass(frozen=True)
class Pose2D:
    x: float; y: float; yaw: float=0.0

@dataclass
class Provenance:
    observation_id: str; agent_id: str; sensor_id: str
    calibration_version: str='synthetic-v1'; parent_ids: list[str]=field(default_factory=list)

@dataclass
class Observation:
    modality: str; value: float; confidence: float; reliability: float; timestamp: float; pose: Pose2D
    spatial_uncertainty: float; valid_for: float; provenance: Provenance; raw: dict[str,Any]=field(default_factory=dict)
    def stale(self, now: float)->bool: return now>self.timestamp+self.valid_for

@dataclass
class Agent:
    agent_id: str; kind: str; pose: Pose2D; speed: float; battery: float; comm_range: float; sensors: list[str]
    current_task: str|None=None; failed: bool=False

@dataclass
class Survivor:
    survivor_id: str; pose: Pose2D; urgency: float; thermal: float=1.; acoustic: float=.7; motion: float=.5; visibility: float=.6

@dataclass
class Hazard:
    kind: str; pose: Pose2D; radius: float; severity: float; growth: float

@dataclass
class Hypothesis:
    hypothesis_id: str; pose: Pose2D; score: float; uncertainty: float
    supporting: list[str]=field(default_factory=list); contradicting: list[str]=field(default_factory=list)
    status: str='UNCONFIRMED'; urgency: float=.5; accessibility: float=.5; hazard: float=0.

@dataclass
class PriorityEstimate:
    site_id: str; score: float; low: float; high: float; decomposition: dict[str,float]; rank_instability: float
