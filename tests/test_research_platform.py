from rescuemind import (
    Agent,
    Allocator,
    CommunicationNetwork,
    ConflictDetector,
    DisasterWorld,
    Fusion,
    Hypothesis,
    Observation,
    Pose2D,
    PriorityModel,
    Provenance,
    ReliabilityState,
    SensorSuite,
    TemporalBuffer,
    run_simulation,
)


def test_deterministic() -> None:
    assert run_simulation(3, 5)["metrics"] == run_simulation(3, 5)["metrics"]


def test_reliability_degrades() -> None:
    world = DisasterWorld(1)
    suite = SensorSuite(world)
    pose = Pose2D(24, 27)
    world.step()
    quality_before, _ = suite.reliability("rgb", pose, 1)
    world.hazard[27, 24] = 1
    quality_after, state = suite.reliability("rgb", pose, 2)
    assert quality_after < quality_before
    assert state in {ReliabilityState.DEGRADED, ReliabilityState.UNCERTAIN}


def test_provenance_duplicate_rejection() -> None:
    provenance = Provenance("x", "a", "s")
    observation = Observation(
        "thermal",
        0.9,
        0.9,
        0.9,
        0,
        Pose2D(1, 1),
        1,
        2,
        provenance,
    )
    assert Fusion.reliability([observation, observation]) == Fusion.reliability(
        [observation]
    )


def test_stale_rejection_and_conflict() -> None:
    buffer = TemporalBuffer(2)
    first = Observation(
        "thermal",
        0.9,
        0.9,
        0.8,
        0,
        Pose2D(0, 0),
        1,
        1,
        Provenance("1", "a", "t"),
    )
    buffer.add(first)
    assert not buffer.aligned(3)
    second = Observation(
        "rgb",
        0.1,
        0.9,
        0.8,
        0,
        Pose2D(0, 0),
        1,
        3,
        Provenance("2", "b", "r"),
    )
    assert ConflictDetector.detect([first, second])


def test_priority_decomposition() -> None:
    estimate = PriorityModel().score(
        Hypothesis(
            "S",
            Pose2D(1, 1),
            0.8,
            0.2,
            urgency=0.9,
            accessibility=0.7,
            hazard=0.2,
        ),
        10,
    )
    assert abs(sum(estimate.decomposition.values()) - estimate.score) < 1e-9
    assert estimate.low < estimate.score < estimate.high


def test_allocators_and_loss() -> None:
    agents = [
        Agent("a", "UAV", Pose2D(0, 0), 2, 1, 10, ["thermal"]),
        Agent("b", "UGV", Pose2D(9, 9), 1, 1, 8, ["acoustic"]),
    ]
    targets = [Hypothesis("S", Pose2D(3, 3), 0.8, 0.3)]
    for method in ["nearest", "greedy", "information_gain", "communication_aware"]:
        assert Allocator.allocate(agents, targets, method)

    network = CommunicationNetwork(0, loss=1)
    network.send(0, {"x": 1})
    assert network.dropped == 1
    assert not network.receive(2)


def test_end_to_end_core() -> None:
    result = run_simulation(2, 8, loss=0.3)
    metrics = result["metrics"]
    assert len(result["agents"]) == 3
    assert metrics["twin_revisions"] >= 16
    assert metrics["messages_dropped"] > 0
    assert "brier" in metrics
