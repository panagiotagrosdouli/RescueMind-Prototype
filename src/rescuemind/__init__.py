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
from .priority import PriorityContext, PriorityWeights, ProbabilisticPriorityEngine
from .simulation import DisasterWorld, SensorSuite, TemporalBuffer
from .spatial import (
    AssociationMetrics,
    AssignmentResult,
    MahalanobisAssociator,
    SpatialMatch,
    evaluate_associations,
)
from .temporal import AlignedObservation, AsynchronousObservationBuffer, ClockOffsetRegistry

__version__ = "0.2.0"

__all__ = [
    "Agent",
    "AlignedObservation",
    "Allocator",
    "AssociationMetrics",
    "AssignmentResult",
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
    "MahalanobisAssociator",
    "Observation",
    "Pose2D",
    "PriorityContext",
    "PriorityEstimate",
    "PriorityModel",
    "PriorityWeights",
    "ProbabilisticPriorityEngine",
    "Provenance",
    "ReliabilityState",
    "SensorSuite",
    "SpatialMatch",
    "Survivor",
    "TemporalBuffer",
    "calibration_metrics",
    "evaluate_associations",
    "run_simulation",
]
