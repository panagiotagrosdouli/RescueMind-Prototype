"""RescueMind synthetic multi-agent disaster intelligence research prototype."""

from .active_perception import (
    CollaborativePerceptionPlanner,
    PerceptionAssignment,
    PerceptionBid,
    PerceptionPlan,
    PerceptionTarget,
    Viewpoint,
)
from .allocation import (
    AgentTaskBid,
    AllocationResult,
    InspectionTask,
    RiskAwareAllocator,
    TaskAssignment,
)
from .decision import Allocator, CommunicationNetwork, DigitalTwin, Explainer, PriorityModel
from .execution import ExecutionEvent, MissionExecutor, MissionTask, TaskState
from .frontier import (
    FREE,
    OCCUPIED,
    UNKNOWN,
    Frontier,
    FrontierAssignment,
    FrontierBid,
    FrontierExplorer,
    FrontierPlan,
)
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
from .network import (
    DeliveryRecord,
    MeshNetworkSimulator,
    NetworkLink,
    NetworkMessage,
    NetworkMetrics,
    NetworkNode,
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
from .twin import LivingDisasterTwin, TwinEvent, TwinSnapshot

__version__ = "0.2.0"

__all__ = [
    "FREE",
    "OCCUPIED",
    "UNKNOWN",
    "Agent",
    "AgentTaskBid",
    "AlignedObservation",
    "AllocationResult",
    "Allocator",
    "AssociationMetrics",
    "AssignmentResult",
    "AsynchronousObservationBuffer",
    "ClockOffsetRegistry",
    "CollaborativePerceptionPlanner",
    "CommunicationNetwork",
    "ConflictDetector",
    "DeliveryRecord",
    "DigitalTwin",
    "DisasterWorld",
    "ExecutionEvent",
    "Explainer",
    "Frontier",
    "FrontierAssignment",
    "FrontierBid",
    "FrontierExplorer",
    "FrontierPlan",
    "Fusion",
    "Hazard",
    "Hypothesis",
    "InspectionTask",
    "LivingDisasterTwin",
    "MahalanobisAssociator",
    "MeshNetworkSimulator",
    "MissionExecutor",
    "MissionTask",
    "NetworkLink",
    "NetworkMessage",
    "NetworkMetrics",
    "NetworkNode",
    "Observation",
    "PerceptionAssignment",
    "PerceptionBid",
    "PerceptionPlan",
    "PerceptionTarget",
    "Pose2D",
    "PriorityContext",
    "PriorityEstimate",
    "PriorityModel",
    "PriorityWeights",
    "ProbabilisticPriorityEngine",
    "Provenance",
    "ReliabilityState",
    "RiskAwareAllocator",
    "SensorSuite",
    "SpatialMatch",
    "Survivor",
    "TaskAssignment",
    "TaskState",
    "TemporalBuffer",
    "TwinEvent",
    "TwinSnapshot",
    "Viewpoint",
    "calibration_metrics",
    "evaluate_associations",
    "run_simulation",
]
