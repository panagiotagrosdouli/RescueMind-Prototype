# Probabilistic Rescue Priority Engine

The priority engine converts a survivor hypothesis and an operational context into a bounded, decomposable decision-support estimate.

## Utility terms

Positive contributions:

- estimated survivor presence;
- urgency;
- survivability under current hazard;
- accessibility;
- expected information gain.

Negative contributions:

- travel time;
- site hazard;
- responder risk;
- communication degradation;
- verification cost.

All inputs are clipped to documented ranges and all weights are normalized before scoring. The returned estimate includes a lower and upper bound whose width increases with epistemic uncertainty, degraded communications, and hazard.

## Ranking rule

Hypotheses are ranked by the conservative lower bound rather than the point estimate. This prevents a highly uncertain candidate from outranking a more stable candidate solely because of a marginally larger mean score.

## Information gain

Expected information gain is approximated as binary entropy of the survivor-presence probability multiplied by hypothesis uncertainty. It is highest when presence is ambiguous and uncertainty is high, supporting verification-oriented tasks without equating uncertainty with rescue priority.

## Responsible scope

The engine is deterministic synthetic research software. Its coefficients are not learned from emergency-response outcomes, clinical data, or real deployments. The score must not be interpreted as a probability of survival or used as an autonomous dispatch decision.
