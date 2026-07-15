# Communication Network Simulator

The communication layer models logical message transport for synthetic multi-agent experiments.

## Included behavior

- directed or bidirectional mesh links;
- shortest-latency routing;
- relay nodes;
- per-link latency and bandwidth;
- serialization queues and congestion delay;
- deterministic seeded packet loss;
- node and link failures;
- message TTL expiration;
- delivery ratio and mean-latency metrics.

## Explicit assumptions

Bandwidth is represented as bytes per simulation-time unit. Link scheduling is deterministic and FIFO per directed link. Routing minimizes configured link latency and does not currently include queue occupancy in route selection.

## Limitations

This module is not a radio propagation model, network protocol stack, ROS 2 DDS emulator, or hardware-in-the-loop communication system. It does not model interference, modulation, antenna orientation, terrain attenuation, retransmission protocols, encryption overhead, or clock synchronization. Results must be described as synthetic communication experiments only.
