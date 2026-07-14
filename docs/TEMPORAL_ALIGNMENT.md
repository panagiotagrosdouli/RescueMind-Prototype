# Temporal Alignment

**Status:** Research Prototype

RescueMind treats timestamps, arrival times, and clock offsets as distinct quantities. The temporal layer corrects source-clock offsets, records out-of-order arrivals, rejects duplicates, marks delayed packets, and excludes stale observations from current fusion windows.

## Guarantees in the current prototype

- Observation IDs are deduplicated before alignment.
- Source-clock offsets are applied without mutating the original observation.
- Alignment output is ordered by corrected timestamp.
- Observations outside the configured temporal window are excluded.
- Observations older than both the system stale threshold and their own validity interval are rejected.
- Delayed arrivals and out-of-order reception are retained as explicit metadata.

## Limitations

- Clock offsets are configured externally rather than estimated online.
- No interpolation is performed for categorical evidence.
- The implementation does not claim synchronization guarantees for physical robots or ROS2 clocks.
- ROS2 and hardware timing validation remain pending.
