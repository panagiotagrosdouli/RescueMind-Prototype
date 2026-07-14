# System Architecture

## 1. Purpose

This document defines the initial software and research architecture of RescueMind Prototype. The architecture is intentionally modular so that perception, mapping, coordination, and rescue-priority estimation can be evaluated independently before being integrated into a complete experimental pipeline.

## 2. Architectural Objectives

The system should:

- support heterogeneous robotic agents and sensing platforms;
- represent uncertainty explicitly throughout the processing chain;
- preserve observation provenance and temporal validity;
- operate under partial observability and intermittent communication;
- permit reproducible experiments and ablation studies;
- separate machine inference from human-facing recommendations;
- remain extensible across simulation and physical platforms.

## 3. Logical Layers

### 3.1 Agent and Sensor Layer

This layer represents aerial robots, ground robots, and deployable sensor nodes. Each agent exposes its state, capabilities, sensing modalities, communication constraints, and operational risk profile.

### 3.2 Observation Layer

Raw measurements are converted into typed observations with timestamps, coordinate frames, source identifiers, quality indicators, and uncertainty descriptors.

### 3.3 Perception Layer

Modality-specific components infer task-relevant features such as thermal anomalies, acoustic events, human-shape hypotheses, motion cues, structural hazards, and traversability estimates.

### 3.4 Fusion Layer

The fusion layer aligns observations in time and space, resolves data associations, combines compatible evidence, detects contradictions, and propagates uncertainty.

### 3.5 Living Disaster Twin

The world model maintains a dynamic probabilistic representation of geometry, accessibility, hazards, agent state, communication coverage, and survivor hypotheses.

### 3.6 Coordination Layer

Coordination components allocate exploration and sensing tasks by balancing information gain, urgency, platform capability, energy constraints, communication quality, and risk.

### 3.7 Rescue Priority Layer

Candidate intervention locations are ranked through a transparent model that incorporates evidence of human presence, survivability indicators, accessibility, hazard severity, intervention time, and uncertainty.

### 3.8 Human Decision-Support Layer

The interface presents priority estimates together with supporting observations, confidence, alternative hypotheses, route options, and known limitations. Recommendations remain advisory.

## 4. Core Data Entities

Initial entities include:

- `AgentState`
- `SensorObservation`
- `PerceptionHypothesis`
- `SpatialEvidence`
- `HazardEstimate`
- `SurvivorHypothesis`
- `MapCellState`
- `RescuePriorityEstimate`
- `TaskAllocation`
- `ExperimentRecord`

Each derived entity should retain provenance metadata linking it to source observations and processing steps.

## 5. Information Flow

```text
Sensors and robot state
        │
        ▼
Typed observations
        │
        ▼
Modality-specific inference
        │
        ▼
Temporal and spatial association
        │
        ▼
Probabilistic evidence fusion
        │
        ▼
Living Disaster Twin
        │
        ├──────────────► Coordination and exploration
        │
        ▼
Rescue Priority estimation
        │
        ▼
Human-interpretable decision support
```

## 6. Uncertainty Representation

The project will initially compare simple probabilistic representations before adopting more complex methods. Candidate approaches include:

- calibrated probability distributions;
- Bayesian updates;
- covariance-based state estimates;
- evidential reasoning;
- ensembles and Monte Carlo uncertainty;
- confidence intervals derived from repeated simulation trials.

The chosen representation must remain inspectable and suitable for sensitivity analysis.

## 7. Failure and Degradation Modes

The architecture must support experiments involving:

- sensor dropout;
- delayed observations;
- localization drift;
- inconsistent coordinate frames;
- false survivor indications;
- communication partitioning;
- agent loss;
- shifting obstacles and hazards;
- severe class imbalance;
- out-of-distribution conditions.

Failures should be surfaced explicitly rather than silently converted into confident predictions.

## 8. Implementation Strategy

Development will proceed from typed domain models and deterministic baselines toward probabilistic and learned components. Each module should expose a narrow interface, unit tests, configuration parameters, and machine-readable outputs.

ROS 2 integration will be introduced after the core computational interfaces are stable enough to avoid coupling the research logic prematurely to middleware-specific details.
