"""RescueMind synthetic multi-agent disaster intelligence research prototype."""

from .decision import Allocator, CommunicationNetwork, DigitalTwin, Explainer, PriorityModel
from .fusion import ConflictDetector, Fusion, calibration_metrics
from .models import (
    Agent,
    Hazard,
    Hypothesis,
    Observation,
    Pose2D,
    PriorityEstimate,
    Provenance,
    ReliabilityState,
    Survivor,
)
from .pipeline import run_simulation
from .simulation import DisasterWorld, SensorSuite, TemporalBuffer
from .temporal import AlignedObservation, AsynchronousObservationBuffer, ClockOffsetRegistry

__version__ = "0.2.0"

__all__ = [
    "Agent",
    "AlignedObservation",
    "Allocator",
    "AsynchronousObservationBuffer",
    "ClockOffsetRegistry",
    "CommunicationNetwork",
    "ConflictDetector",
    "DigitalTwin",
    "DisasterWorld",
    "Explainer",
    "Fusion",
    "Hazard",
    "Hypothesis",
    "Observation",
    "Pose2D",
    "PriorityEstimate",
    "PriorityModel",
    "Provenance",
    "ReliabilityState",
    "SensorSuite",
    "Survivor",
    "TemporalBuffer",
    "calibration_metrics",
    "run_simulation",
]
