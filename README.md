# RescueMind Prototype

> Uncertainty-aware multi-agent perception and human-supervised rescue decision support in synthetic post-disaster environments.

[Research vision and system rationale](https://github.com/panagiotagrosdouli/RescueMind)

## Verified scope

RescueMind-Prototype is a **research prototype** validated only in deterministic synthetic simulations. It implements a CPU-only integrated pipeline with UAV, UGV, and static sensing agents; multimodal observations; reliability-aware fusion; a dynamic disaster twin; survivor hypotheses; interpretable rescue-priority estimates; degraded communication; task allocation; and grounded explanations.

It is **not** an operational command system, medical device, structural-assessment tool, or autonomous rescue authority. It has not been field-, hardware-, ROS2-, or external-dataset validated.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python scripts/run_all.py --mode smoke
python scripts/run_benchmark_suite.py --num-seeds 5
```

Run modes: `smoke`, `perception`, `fusion`, `digital-twin`, `coordination`, `priority`, `benchmark`, `full`.

## Implemented research components

| Component | Status |
|---|---|
| Deterministic 2D disaster simulation | Research Prototype |
| UAV, UGV, static sensor node | Implemented |
| Thermal, RGB, acoustic, radar, environmental observations | Synthetic Validation |
| Depth capability/accessibility scaffold | Experimental |
| Reliability states and environment-dependent degradation | Implemented |
| Temporal buffering and stale-data rejection | Implemented |
| Fixed, reliability-weighted, Bayesian fusion | Implemented |
| Provenance and duplicate rejection | Implemented |
| Modality conflict detection | Implemented |
| Dynamic Living Disaster Twin | Research Prototype |
| Survivor hypothesis lifecycle subset | Experimental |
| Dynamic fire hazard and blocked-access evolution | Research Prototype |
| Decomposable Rescue Priority Index with intervals | Implemented |
| Priority reversal metric | Implemented |
| Nearest, greedy, information-gain, communication-aware allocation | Implemented |
| Packet loss and delayed-message simulation | Implemented |
| Grounded explanation and counterfactual | Research Prototype |
| Brier, ECE, MCE, precision, recall, F1 metrics | Synthetic Validation |
| GIF and MP4 generation pipeline | Implemented when encoder is available |
| ROS2 runtime | Pending ROS2 Validation |
| External datasets | Pending Dataset Validation |
| Physical robots | Pending Hardware Validation |

## Architecture

`world → heterogeneous agents → synthetic sensors → reliability → temporal alignment → fusion → conflict detection → hypotheses → disaster twin → rescue priority → allocation → explanation`

## Reproducibility evidence

The implementation session executed installation, tests, all principal run modes, and a five-seed benchmark. The exact commands, repaired Bayesian-fusion failure, limitations, and blockers are recorded in `WORK_LOG.md`, `docs/REPOSITORY_AUDIT.md`, `STATUS.yaml`, and `BLOCKERS.md`.

Each run writes generated metrics, manifests, figures, a report, a GIF, and an MP4 or an explicit encoder blocker. Quantitative outputs are synthetic and must not be interpreted as emergency-response performance.

## Docker

```bash
docker build -t rescuemind .
docker run --rm -v "$(pwd)/results:/app/results" rescuemind python scripts/run_all.py --mode smoke
```

The Dockerfile is provided, but local daemon validation was unavailable during the implementation session and is not claimed.

## Responsible use

All rankings are labelled decision support. Human operators retain authority to confirm, reject, override, or request additional evidence. The current prototype must not be deployed in real emergencies.
