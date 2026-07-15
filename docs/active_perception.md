# Collaborative Active Perception

The active-perception layer coordinates a small synthetic robot team around explicit candidate viewpoints. It prioritizes expected uncertainty reduction while accounting for travel time, sensor modality coverage, risk, communication quality, and duplicate coverage.

## Core model

- `PerceptionTarget` stores location, uncertainty, required modalities, and priority.
- `Viewpoint` stores expected observation quality, visible modalities, communication quality, and risk.
- `PerceptionBid` exposes every utility component and rejection reason.
- `CollaborativePerceptionPlanner.plan` computes an exact one-agent-to-one-target assignment for up to 18 targets.

The uncertainty update is a bounded scalar approximation, not a Bayesian filter. The exact solver is intended for reproducible small-team experiments and raises explicitly for larger target sets.

## Limitations

This module does not generate collision-free trajectories, model camera geometry, solve SLAM, control physical robots, or guarantee emergency-response performance. Candidate viewpoints and observation quality must be provided by the synthetic experiment.
