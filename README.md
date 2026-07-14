# RescueMind Prototype

> **A research software platform for uncertainty-aware, multi-agent disaster perception and operational rescue prioritization.**

RescueMind Prototype is the implementation repository of the broader [RescueMind research initiative](https://github.com/panagiotagrosdouli/RescueMind). It provides the computational foundation for studying how heterogeneous robotic agents can transform fragmented, noisy, and incomplete observations into interpretable decision support for post-disaster urban search and rescue.

The project is motivated by a central operational question:

> **How can distributed robotic perception be converted into calibrated, actionable, and human-interpretable rescue intelligence under severe uncertainty?**

The repository is designed as a modular experimental platform rather than a monolithic application. It will support reproducible simulation studies, probabilistic sensor fusion, dynamic mapping, multi-agent coordination, rescue-priority estimation, and human-facing evaluation.

## Research Scope

RescueMind investigates the intersection of:

- heterogeneous multi-robot systems;
- collaborative and distributed perception;
- multimodal sensor fusion;
- uncertainty-aware machine learning;
- probabilistic spatial mapping;
- autonomous exploration and task allocation;
- edge intelligence under degraded connectivity;
- explainable decision support for emergency response.

The software is intended to support research questions concerning not only whether a survivor-related signal can be detected, but also how evidence should be combined, ranked, explained, and updated as the environment evolves.

## Relation to the Main Repository

The scientific motivation, conceptual architecture, research questions, and long-term vision are maintained in:

**[panagiotagrosdouli/RescueMind](https://github.com/panagiotagrosdouli/RescueMind)**

This repository contains the implementation layer: source code, simulation environments, configuration files, experiments, benchmarks, tests, and technical documentation.

## System Objectives

The initial development programme focuses on six tightly connected capabilities.

### 1. Heterogeneous Agent Modelling

Represent aerial robots, ground robots, and deployable sensing nodes with distinct sensing, mobility, endurance, communication, and risk characteristics.

### 2. Multimodal Perception

Process synthetic and, later, real observations from thermal cameras, RGB sensors, depth sensors, microphones, radar, environmental sensors, and robot-state estimators.

### 3. Uncertainty-Aware Sensor Fusion

Combine asynchronous and potentially contradictory observations while preserving confidence, provenance, temporal validity, and spatial consistency.

### 4. Living Disaster Twin

Maintain a continuously updated probabilistic representation of the affected environment, including geometry, accessibility, hazards, survivor hypotheses, and confidence estimates.

### 5. Rescue Priority Estimation

Develop and evaluate a transparent Rescue Priority Index that ranks candidate intervention locations using evidence of human presence, survivability indicators, accessibility, structural risk, expected intervention time, and model uncertainty.

### 6. Human-Centred Decision Support

Expose the evidence behind each recommendation, communicate uncertainty explicitly, and preserve human authority over operational decisions.

## Conceptual Processing Pipeline

```text
Robot and sensor observations
            │
            ▼
Temporal alignment and validation
            │
            ▼
Modality-specific perception
            │
            ▼
Uncertainty-aware evidence fusion
            │
            ▼
Dynamic probabilistic world model
            │
            ▼
Survivor and hazard hypotheses
            │
            ▼
Rescue Priority Index
            │
            ▼
Human-interpretable decision support
```

## Scientific Design Principles

The implementation will be guided by the following principles:

- **Explicit uncertainty:** predictions must include calibrated confidence rather than binary certainty.
- **Traceable evidence:** every derived hypothesis should retain links to its supporting observations.
- **Modularity:** perception, mapping, coordination, and prioritization components should be independently testable.
- **Reproducibility:** experiments should be configuration-driven and produce machine-readable outputs.
- **Graceful degradation:** the system should remain interpretable under sensor failure, missing data, or communication loss.
- **Human oversight:** the software provides decision support and does not autonomously make life-critical decisions.
- **Operational realism:** evaluation should include occlusion, dust, darkness, noise, localization drift, intermittent networks, and evolving hazards.

## Planned Repository Structure

```text
RescueMind-Prototype/
├── README.md
├── pyproject.toml
├── requirements.txt
├── LICENSE
├── .gitignore
├── configs/
│   └── default.yaml
├── docs/
│   ├── system_architecture.md
│   ├── research_hypothesis.md
│   ├── evaluation_protocol.md
│   └── design_decisions.md
├── src/
│   └── rescuemind/
│       ├── perception/
│       ├── sensor_fusion/
│       ├── mapping/
│       ├── coordination/
│       ├── rescue_priority/
│       ├── digital_twin/
│       └── utils/
├── simulations/
├── experiments/
├── examples/
└── tests/
```

## Initial Technology Direction

The exact stack will evolve with the experimental requirements. The current technical direction includes:

- Python 3.11+
- ROS 2
- NumPy and SciPy
- PyTorch
- OpenCV
- Open3D
- NetworkX
- Pydantic
- PyYAML
- pytest
- Gazebo or Isaac Sim
- Docker
- GitHub Actions

Dependencies will be introduced only when they support a concrete, documented requirement.

## Evaluation Strategy

The project will be evaluated progressively, beginning with controlled synthetic scenarios and advancing toward more realistic robotic experiments.

Core evaluation dimensions include:

- survivor-detection sensitivity and false-alarm rate;
- probabilistic calibration;
- spatial localization error;
- map consistency under changing conditions;
- robustness to missing or conflicting sensor data;
- communication efficiency;
- prioritization stability;
- explanation fidelity;
- computational latency;
- performance under degraded sensing and connectivity.

A baseline is considered meaningful only when the experimental assumptions, data generation process, metrics, and limitations are documented.

## Development Stages

1. **Foundation** — package structure, configuration system, data models, tests, and continuous integration.
2. **Simulation baseline** — synthetic disaster environments and heterogeneous agent models.
3. **Perception baseline** — modality-specific observation models and survivor-related signal detection.
4. **Fusion layer** — probabilistic evidence integration with confidence and provenance tracking.
5. **Dynamic world model** — Living Disaster Twin and spatial hypothesis management.
6. **Priority model** — interpretable Rescue Priority Index with sensitivity analysis.
7. **Coordination** — information-driven exploration and task allocation.
8. **Human interface** — evidence views, uncertainty communication, and decision-support experiments.
9. **Hardware validation** — controlled tests on selected aerial, ground, or sensing platforms.

## Current Status

**Research software foundation stage.**

The complete system described above has not yet been implemented or operationally validated. The repository will document incremental prototypes, negative results, limitations, assumptions, and experimental evidence as development progresses.

## Responsible Research Statement

RescueMind is intended for humanitarian research and decision-support experimentation. Any future deployment in real emergency operations would require extensive validation, collaboration with certified rescue professionals, safety engineering, cybersecurity assessment, regulatory compliance, and controlled field testing.

No model output should be interpreted as a substitute for professional emergency-response judgement.

## Author

**Panagiota Grosdouli**  
Electrical and Computer Engineering

## Licence

Licensing information will be defined before the first public software release.
