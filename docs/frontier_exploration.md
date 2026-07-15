# Frontier Exploration

`FrontierExplorer` turns a discrete occupancy grid into auditable exploration targets for small synthetic multi-agent experiments.

## Map convention

- `UNKNOWN = -1`
- `FREE = 0`
- `OCCUPIED = 1`

A frontier cell is a free cell with at least one four-connected unknown neighbour. Connected frontier cells are grouped into clusters, and each cluster receives a deterministic identifier and centroid.

## Scoring inputs

Each frontier records:

- the number of nearby unknown cells as an information-gain proxy;
- mean hazard;
- mean survivor-interest signal;
- mean communication quality.

Agent bids then subtract travel and hazard costs while rewarding information gain, survivor interest, and communication quality. Failed agents, invalid speeds, and insufficient battery produce explicit infeasibility reasons.

## Assignment

The planner computes an exact one-agent-to-one-frontier assignment for up to 18 frontiers. The output includes selected assignments, all bids, unassigned frontiers, and idle agents.

## Scope and limitations

This subsystem is intended for deterministic algorithm experiments. It does not perform SLAM, continuous-space path planning, obstacle avoidance, radio propagation modelling, or physical robot control. Grid layers and scoring coefficients are synthetic and are not validated for operational rescue decisions.
