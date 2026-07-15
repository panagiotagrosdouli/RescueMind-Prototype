# Bayesian World Model

The Bayesian world model maintains a separate Beta-distributed belief for each synthetic survivor hypothesis.

## State

Each `SurvivorBelief` stores:

- Beta parameters `alpha` and `beta`;
- posterior probability of survivor presence;
- approximate credible interval;
- monotonic update timestamp;
- evidence identifiers and contributing modalities.

## Evidence updates

`BayesianEvidence` is binary and reliability weighted. Supporting evidence increments `alpha`; contradictory evidence increments `beta`. Duplicate evidence identifiers and out-of-order timestamps are rejected to preserve an auditable update history.

## Temporal decay

Evidence strength decays exponentially toward the configured prior. The posterior mean therefore moves toward the prior probability as observations become old, without deleting provenance.

## Re-observation

A hypothesis is flagged for re-observation when:

- its approximate credible interval remains wider than the configured threshold; or
- its latest evidence is older than the configured staleness threshold.

## Statistical limitation

Credible intervals use a bounded normal approximation to the Beta distribution. This is deterministic and dependency-free, but it is less accurate for highly skewed or very low-count posteriors than exact Beta quantiles.

## Responsible scope

This module is synthetic decision-support research software. Its probabilities are model beliefs, not clinically or operationally validated survival probabilities. Sensor likelihood calibration, dependence between modalities, and real-world validation remain future work.
