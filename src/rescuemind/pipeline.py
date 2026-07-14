from __future__ import annotations

import math
from dataclasses import asdict

from .decision import Allocator, CommunicationNetwork, DigitalTwin, Explainer, PriorityModel
from .fusion import ConflictDetector, Fusion, calibration_metrics
from .models import Agent, Hypothesis, Observation, Pose2D
from .simulation import DisasterWorld, SensorSuite, TemporalBuffer


def run_simulation(
    seed: int = 0,
    steps: int = 18,
    loss: float = 0.15,
    method: str = "reliability",
) -> dict:
    world = DisasterWorld(seed)
    sensors = SensorSuite(world)
    agents = [
        Agent("UAV-1", "UAV", Pose2D(20, 20), 3, 1, 18, ["thermal", "rgb"]),
        Agent(
            "UGV-1",
            "UGV",
            Pose2D(5, 5),
            1,
            1,
            10,
            ["acoustic", "radar", "depth"],
        ),
        Agent(
            "NODE-1",
            "STATIC",
            Pose2D(12, 28),
            0,
            1,
            14,
            ["acoustic", "environmental"],
        ),
    ]
    network = CommunicationNetwork(seed, loss)
    buffer = TemporalBuffer()
    twin = DigitalTwin(world)
    traces: list[dict] = []
    labels: list[int] = []
    probabilities: list[float] = []
    ranks: list[list[str]] = []
    all_conflicts: list[dict] = []

    fusion_method = {
        "fixed": Fusion.fixed,
        "bayes": Fusion.bayes,
    }.get(method, Fusion.reliability)

    for timestamp in range(steps):
        world.step()
        for index, agent in enumerate(agents[:2]):
            target = world.survivors[index]
            dx = target.pose.x - agent.pose.x
            dy = target.pose.y - agent.pose.y
            distance = max(1.0, math.hypot(dx, dy))
            agent.pose = Pose2D(
                agent.pose.x + agent.speed * dx / distance,
                agent.pose.y + agent.speed * dy / distance,
            )

        for agent in agents:
            for modality in agent.sensors:
                if modality == "depth":
                    continue
                for survivor in world.survivors:
                    observation = sensors.observe(
                        agent,
                        survivor,
                        modality,
                        timestamp,
                    )
                    buffer.add(observation)
                    network.send(timestamp, asdict(observation))

        delivered = network.receive(timestamp)
        aligned = buffer.aligned(timestamp)
        hypotheses: list[Hypothesis] = []

        for survivor in world.survivors:
            local_observations = [
                observation
                for observation in aligned
                if math.hypot(
                    observation.pose.x - survivor.pose.x,
                    observation.pose.y - survivor.pose.y,
                )
                < 2.0
            ]
            probability, uncertainty = fusion_method(local_observations)
            hypothesis = Hypothesis(
                survivor.survivor_id,
                survivor.pose,
                probability,
                uncertainty,
                [
                    observation.provenance.observation_id
                    for observation in local_observations
                    if observation.value >= 0.5
                ],
                [
                    observation.provenance.observation_id
                    for observation in local_observations
                    if observation.value < 0.3
                ],
                urgency=survivor.urgency,
            )
            x = int(hypothesis.pose.x)
            y = int(hypothesis.pose.y)
            hypothesis.hazard = float(world.hazard[y, x])
            hypothesis.accessibility = float(world.accessibility[y, x])
            if probability > 0.75:
                hypothesis.status = "HIGH_PRIORITY"
            elif probability > 0.6:
                hypothesis.status = "PROBABLE"
            elif probability > 0.45:
                hypothesis.status = "POSSIBLE"
            else:
                hypothesis.status = "REQUIRES_REOBSERVATION"
            twin.update(hypothesis, timestamp)
            hypotheses.append(hypothesis)
            labels.append(1)
            probabilities.append(probability)

        negative_observations = [
            observation for observation in aligned if observation.modality == "thermal"
        ][:2]
        negative_probability, _ = Fusion.reliability(
            [
                Observation(
                    observation.modality,
                    max(0.0, observation.value - 0.55),
                    observation.confidence,
                    observation.reliability,
                    observation.timestamp,
                    Pose2D(2, 2),
                    observation.spatial_uncertainty,
                    observation.valid_for,
                    observation.provenance,
                    observation.raw,
                )
                for observation in negative_observations
            ]
        )
        labels.append(0)
        probabilities.append(negative_probability)

        priorities = [
            PriorityModel().score(
                hypothesis,
                math.hypot(hypothesis.pose.x - 5, hypothesis.pose.y - 5),
            )
            for hypothesis in hypotheses
        ]
        priorities.sort(key=lambda estimate: estimate.score, reverse=True)
        ranks.append([estimate.site_id for estimate in priorities])
        allocation = Allocator.allocate(
            agents,
            hypotheses,
            "communication_aware",
            1.0 - loss,
        )
        conflicts: list[dict] = []
        for hypothesis in hypotheses:
            conflicts.extend(
                ConflictDetector.detect(
                    [
                        observation
                        for observation in aligned
                        if observation.pose == hypothesis.pose
                    ]
                )
            )
        all_conflicts.extend(conflicts)
        top_hypothesis = next(
            hypothesis
            for hypothesis in hypotheses
            if hypothesis.hypothesis_id == priorities[0].site_id
        )
        explanation = Explainer.explain(
            priorities[0],
            top_hypothesis,
            conflicts,
            priorities[1:],
        )
        traces.append(
            {
                "t": timestamp,
                "agents": [asdict(agent) for agent in agents],
                "hypotheses": [asdict(hypothesis) for hypothesis in hypotheses],
                "priorities": [asdict(estimate) for estimate in priorities],
                "allocation": allocation,
                "delivered_messages": len(delivered),
                "conflicts": conflicts,
                "explanation": explanation,
            }
        )

    reversals = sum(
        ranks[index][0] != ranks[index - 1][0]
        for index in range(1, len(ranks))
    )
    metrics = calibration_metrics(labels, probabilities) | {
        "rank_reversals": reversals,
        "messages_sent": network.sent,
        "messages_delivered": network.delivered,
        "messages_dropped": network.dropped,
        "packet_loss_observed": network.dropped / max(1, network.sent),
        "twin_revisions": twin.revision,
        "conflicts_detected": len(all_conflicts),
    }
    return {
        "seed": seed,
        "method": method,
        "world": world,
        "agents": agents,
        "twin": twin,
        "traces": traces,
        "metrics": metrics,
    }
