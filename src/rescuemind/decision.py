from __future__ import annotations

import math
import random

import numpy as np

from .models import Agent, Hypothesis, PriorityEstimate


class DigitalTwin:
    def __init__(self, world):
        self.world = world
        self.revision = 0
        self.layers = {
            key: np.zeros((world.size, world.size))
            for key in ["survivor", "uncertainty", "age", "priority"]
        }

    def update(self, hypothesis: Hypothesis, timestamp: float) -> None:
        x = int(round(hypothesis.pose.x))
        y = int(round(hypothesis.pose.y))
        self.layers["survivor"][y, x] = hypothesis.score
        self.layers["uncertainty"][y, x] = hypothesis.uncertainty
        self.layers["age"][y, x] = 0
        self.layers["age"] += 1
        self.revision += 1

    def serialize(self, path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            revision=self.revision,
            **self.layers,
            hazard=self.world.hazard,
            accessibility=self.world.accessibility,
            communication=self.world.comm,
        )


class PriorityModel:
    def __init__(self, weights: dict[str, float] | None = None):
        self.w = weights or {
            "presence": 0.34,
            "urgency": 0.22,
            "survival": 0.14,
            "access": 0.15,
            "hazard": 0.10,
            "time": 0.03,
            "uncertainty": 0.12,
        }

    def score(self, hypothesis: Hypothesis, travel_time: float) -> PriorityEstimate:
        terms = {
            "presence": hypothesis.score,
            "urgency": hypothesis.urgency,
            "survival": max(0.0, 1.0 - hypothesis.hazard * 0.7),
            "access": hypothesis.accessibility,
            "hazard": -hypothesis.hazard,
            "time": -min(1.0, travel_time / 60.0),
            "uncertainty": -hypothesis.uncertainty,
        }
        score = sum(self.w[key] * terms[key] for key in self.w)
        interval = 0.08 + 0.25 * hypothesis.uncertainty
        return PriorityEstimate(
            hypothesis.hypothesis_id,
            float(score),
            float(score - interval),
            float(score + interval),
            {key: self.w[key] * terms[key] for key in self.w},
            float(min(1.0, 2.0 * interval)),
        )


class Allocator:
    @staticmethod
    def allocate(
        agents: list[Agent],
        targets: list[Hypothesis],
        method: str = "greedy",
        comm_quality: float = 1.0,
    ) -> dict[str, str]:
        allocation: dict[str, str] = {}
        available = [agent for agent in agents if not agent.failed]
        for hypothesis in sorted(targets, key=lambda item: item.score, reverse=True):

            def cost(agent: Agent) -> float:
                distance = math.hypot(
                    agent.pose.x - hypothesis.pose.x,
                    agent.pose.y - hypothesis.pose.y,
                ) / max(agent.speed, 0.1)
                capability = (
                    1.0
                    if set(agent.sensors) & {"thermal", "acoustic", "radar", "rgb"}
                    else 0.3
                )
                if method == "nearest":
                    return distance
                if method == "information_gain":
                    return distance - 4.0 * hypothesis.uncertainty * capability
                if method == "communication_aware":
                    return distance + 8.0 * (1.0 - comm_quality) - 2.0 * capability
                return distance - 2.0 * capability

            if available:
                agent = min(available, key=cost)
                allocation[hypothesis.hypothesis_id] = agent.agent_id
                agent.current_task = f"inspect:{hypothesis.hypothesis_id}"
        return allocation


class CommunicationNetwork:
    def __init__(self, seed: int = 0, loss: float = 0.1, delay: int = 1):
        self.r = random.Random(seed)
        self.loss = loss
        self.delay = delay
        self.queue: list[tuple[float, dict]] = []
        self.sent = 0
        self.delivered = 0
        self.dropped = 0

    def send(self, timestamp: float, payload: dict) -> None:
        self.sent += 1
        if self.r.random() < self.loss:
            self.dropped += 1
            return
        self.queue.append((timestamp + self.delay, payload))

    def receive(self, timestamp: float) -> list[dict]:
        ready = [payload for due, payload in self.queue if due <= timestamp]
        self.queue = [item for item in self.queue if item[0] > timestamp]
        self.delivered += len(ready)
        return ready


class Explainer:
    @staticmethod
    def explain(
        priority: PriorityEstimate,
        hypothesis: Hypothesis,
        conflicts: list[dict],
        alternatives: list[PriorityEstimate],
    ) -> dict:
        dominant = sorted(
            priority.decomposition.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:3]
        text = (
            f"{hypothesis.hypothesis_id} is recommended for operator review with score "
            f"{priority.score:.3f} ({priority.low:.3f}–{priority.high:.3f}). "
            "Dominant computed terms: "
            + ", ".join(f"{key}={value:+.3f}" for key, value in dominant)
            + f". Evidence includes {len(hypothesis.supporting)} supporting and "
            f"{len(hypothesis.contradicting)} contradicting observations."
        )
        if conflicts:
            text += f" {len(conflicts)} modality conflict(s) require verification."
        return {
            "decision_support_only": True,
            "text": text,
            "counterfactual": {
                "condition": "independent confirmation",
                "estimated_effect": round(0.12 * (1.0 - hypothesis.uncertainty), 3),
                "statement": (
                    f"{hypothesis.hypothesis_id} priority would increase if an independent "
                    "modality confirms presence and uncertainty decreases."
                ),
            },
            "alternatives": [alternative.site_id for alternative in alternatives[:2]],
        }
