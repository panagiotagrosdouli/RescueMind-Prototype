"""Deterministic mesh-network simulation for synthetic multi-agent experiments.

The simulator models logical communication effects only. It is not a radio,
ROS 2, or physical-network emulator and has not been validated on hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from random import Random
from typing import Any


@dataclass(frozen=True)
class NetworkNode:
    node_id: str
    relay: bool = False
    active: bool = True


@dataclass(frozen=True)
class NetworkLink:
    source: str
    target: str
    latency: float = 1.0
    bandwidth: float = 1024.0
    loss_probability: float = 0.0
    active: bool = True

    def __post_init__(self) -> None:
        if self.latency < 0.0:
            raise ValueError("latency must be non-negative")
        if self.bandwidth <= 0.0:
            raise ValueError("bandwidth must be positive")
        if not 0.0 <= self.loss_probability <= 1.0:
            raise ValueError("loss_probability must be in [0, 1]")


@dataclass(frozen=True)
class NetworkMessage:
    message_id: str
    source: str
    destination: str
    size_bytes: int
    created_at: float
    payload: dict[str, Any] = field(default_factory=dict)
    ttl: float = 60.0

    def __post_init__(self) -> None:
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be positive")
        if self.ttl <= 0.0:
            raise ValueError("ttl must be positive")


@dataclass(frozen=True)
class DeliveryRecord:
    message_id: str
    route: tuple[str, ...]
    delivered_at: float | None
    latency: float | None
    dropped_reason: str | None

    @property
    def delivered(self) -> bool:
        return self.delivered_at is not None


@dataclass(frozen=True)
class NetworkMetrics:
    sent: int
    delivered: int
    dropped: int
    delivery_ratio: float
    mean_latency: float


class MeshNetworkSimulator:
    """Route and transmit messages over a small deterministic mesh graph."""

    def __init__(self, seed: int = 0):
        self.nodes: dict[str, NetworkNode] = {}
        self.links: dict[tuple[str, str], NetworkLink] = {}
        self._next_free: dict[tuple[str, str], float] = {}
        self._random = Random(seed)
        self.records: list[DeliveryRecord] = []

    def add_node(self, node: NetworkNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"duplicate node {node.node_id}")
        self.nodes[node.node_id] = node

    def set_node_active(self, node_id: str, active: bool) -> None:
        node = self.nodes[node_id]
        self.nodes[node_id] = NetworkNode(node.node_id, node.relay, active)

    def add_link(self, link: NetworkLink, bidirectional: bool = True) -> None:
        if link.source not in self.nodes or link.target not in self.nodes:
            raise KeyError("link endpoints must be registered nodes")
        self.links[(link.source, link.target)] = link
        self._next_free.setdefault((link.source, link.target), 0.0)
        if bidirectional:
            reverse = NetworkLink(
                link.target,
                link.source,
                link.latency,
                link.bandwidth,
                link.loss_probability,
                link.active,
            )
            self.links[(reverse.source, reverse.target)] = reverse
            self._next_free.setdefault((reverse.source, reverse.target), 0.0)

    def set_link_active(self, source: str, target: str, active: bool) -> None:
        link = self.links[(source, target)]
        self.links[(source, target)] = NetworkLink(
            link.source,
            link.target,
            link.latency,
            link.bandwidth,
            link.loss_probability,
            active,
        )

    def route(self, source: str, destination: str) -> tuple[str, ...] | None:
        if source not in self.nodes or destination not in self.nodes:
            raise KeyError("unknown network node")
        if not self.nodes[source].active or not self.nodes[destination].active:
            return None
        queue: list[tuple[float, str, tuple[str, ...]]] = [(0.0, source, (source,))]
        best: dict[str, float] = {source: 0.0}
        while queue:
            cost, node_id, path = heappop(queue)
            if node_id == destination:
                return path
            if cost > best.get(node_id, float("inf")):
                continue
            for (left, right), link in sorted(self.links.items()):
                if left != node_id or not link.active or not self.nodes[right].active:
                    continue
                candidate = cost + link.latency
                if candidate < best.get(right, float("inf")):
                    best[right] = candidate
                    heappush(queue, (candidate, right, path + (right,)))
        return None

    def send(self, message: NetworkMessage) -> DeliveryRecord:
        if message.created_at < 0.0:
            raise ValueError("created_at must be non-negative")
        route = self.route(message.source, message.destination)
        if route is None:
            return self._record(message, (), None, "unreachable")
        current_time = message.created_at
        for source, target in zip(route, route[1:]):
            link = self.links[(source, target)]
            if self._random.random() < link.loss_probability:
                return self._record(message, route, None, f"packet_loss:{source}->{target}")
            transmission = message.size_bytes / link.bandwidth
            current_time = max(current_time, self._next_free[(source, target)])
            current_time += transmission + link.latency
            self._next_free[(source, target)] = current_time
            if current_time - message.created_at > message.ttl:
                return self._record(message, route, None, "ttl_expired")
        return self._record(message, route, current_time, None)

    def _record(
        self,
        message: NetworkMessage,
        route: tuple[str, ...],
        delivered_at: float | None,
        reason: str | None,
    ) -> DeliveryRecord:
        latency = None if delivered_at is None else delivered_at - message.created_at
        record = DeliveryRecord(message.message_id, route, delivered_at, latency, reason)
        self.records.append(record)
        return record

    def metrics(self) -> NetworkMetrics:
        delivered_records = [record for record in self.records if record.delivered]
        sent = len(self.records)
        delivered = len(delivered_records)
        dropped = sent - delivered
        mean_latency = (
            sum(record.latency or 0.0 for record in delivered_records) / delivered
            if delivered
            else 0.0
        )
        return NetworkMetrics(
            sent,
            delivered,
            dropped,
            delivered / sent if sent else 1.0,
            mean_latency,
        )
