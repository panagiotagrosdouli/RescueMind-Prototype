# Dynamic Hazard Propagation

This subsystem provides a deterministic, dependency-free grid model for synthetic fire, smoke, and toxic-gas experiments.

## Model

Each cell stores normalized fire, smoke, toxic-gas, flammability, and blocked-state values. Updates are synchronous, so every step is computed from the same previous snapshot.

The model supports:

- four-connected fire spread;
- smoke and toxic-gas diffusion;
- fire-generated smoke;
- configurable decay rates;
- directional wind bias;
- blocked cells that prevent direct transfer;
- immutable snapshots and non-mutating forecasts;
- normalized point-risk queries and unsafe-cell extraction.

## Intended use

The output can feed synthetic route scoring, task allocation, frontier exploration, and Living Disaster Twin experiments. Forecasts preserve the current state, enabling hypothetical planning without changing the active simulation.

## Limitations

This is not a computational-fluid-dynamics solver or a validated fire model. It does not model temperature, buoyancy, combustion chemistry, building materials, turbulent flow, ventilation, weather, or real toxicology. Grid values are synthetic normalized intensities and must not be interpreted as physical measurements or operational safety thresholds.
