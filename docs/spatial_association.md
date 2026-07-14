# Probabilistic Spatial Association

RescueMind uses covariance-aware gating to associate asynchronous observations with existing survivor hypotheses before fusion and lifecycle updates.

## Current model

The current domain model stores scalar spatial uncertainty rather than a full covariance matrix. The implementation therefore treats observation and hypothesis uncertainty as isotropic standard deviations and combines them in quadrature. Candidate pairs are accepted when their Mahalanobis distance is below a configurable threshold.

A dependency-free dynamic-programming solver computes the exact minimum-cost one-to-one assignment for up to 18 hypotheses. Observations may remain unmatched at an explicit miss cost, and unmatched observations can initialize conservative `UNCONFIRMED` hypotheses.

## Evaluation

The module reports correct associations, false associations, missed associations, ID switches, and aggregate association accuracy for labelled synthetic experiments.

## Limitations

- No full anisotropic covariance matrices are available yet.
- The exact assignment solver is intentionally bounded and is not suitable for large scenes.
- No real sensor localization errors, ROS2 transforms, SLAM covariance, or hardware timestamps have been validated.
- Association output is research evidence for downstream decision support; it is not an operational rescue determination.
