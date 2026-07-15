from rescuemind.network import (
    MeshNetworkSimulator,
    NetworkLink,
    NetworkMessage,
    NetworkNode,
)


def build_network(seed: int = 0) -> MeshNetworkSimulator:
    network = MeshNetworkSimulator(seed=seed)
    for node in [
        NetworkNode("uav"),
        NetworkNode("relay", relay=True),
        NetworkNode("base"),
    ]:
        network.add_node(node)
    network.add_link(NetworkLink("uav", "relay", latency=1.0, bandwidth=100.0))
    network.add_link(NetworkLink("relay", "base", latency=2.0, bandwidth=100.0))
    return network


def message(message_id: str = "m-1", size: int = 100, ttl: float = 60.0) -> NetworkMessage:
    return NetworkMessage(message_id, "uav", "base", size, 0.0, ttl=ttl)


def test_routes_through_relay() -> None:
    network = build_network()
    assert network.route("uav", "base") == ("uav", "relay", "base")


def test_delivery_accounts_for_latency_and_transmission_time() -> None:
    record = build_network().send(message())
    assert record.delivered
    assert record.latency == 5.0


def test_bandwidth_queue_creates_congestion_delay() -> None:
    network = build_network()
    first = network.send(message("m-1"))
    second = network.send(message("m-2"))
    assert first.delivered and second.delivered
    assert second.delivered_at > first.delivered_at


def test_node_failure_makes_destination_unreachable() -> None:
    network = build_network()
    network.set_node_active("relay", False)
    record = network.send(message())
    assert not record.delivered
    assert record.dropped_reason == "unreachable"


def test_link_failure_removes_route() -> None:
    network = build_network()
    network.set_link_active("relay", "base", False)
    record = network.send(message())
    assert not record.delivered
    assert record.dropped_reason == "unreachable"


def test_ttl_expiry_is_explicit() -> None:
    record = build_network().send(message(ttl=2.0))
    assert not record.delivered
    assert record.dropped_reason == "ttl_expired"


def test_deterministic_packet_loss() -> None:
    network = MeshNetworkSimulator(seed=3)
    network.add_node(NetworkNode("a"))
    network.add_node(NetworkNode("b"))
    network.add_link(NetworkLink("a", "b", loss_probability=1.0))
    record = network.send(NetworkMessage("m", "a", "b", 1, 0.0))
    assert record.dropped_reason == "packet_loss:a->b"


def test_metrics_summarize_delivery() -> None:
    network = build_network()
    network.send(message("m-1"))
    network.set_node_active("relay", False)
    network.send(message("m-2"))
    metrics = network.metrics()
    assert metrics.sent == 2
    assert metrics.delivered == 1
    assert metrics.dropped == 1
    assert metrics.delivery_ratio == 0.5


def test_validation_rejects_invalid_values() -> None:
    try:
        NetworkLink("a", "b", bandwidth=0.0)
    except ValueError as exc:
        assert "bandwidth" in str(exc)
    else:
        raise AssertionError("invalid bandwidth should fail")
