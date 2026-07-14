from __future__ import annotations

import math
import uuid

import numpy as np

from .models import (
    Agent,
    Hazard,
    Observation,
    Pose2D,
    Provenance,
    ReliabilityState,
    Survivor,
)


class DisasterWorld:
    def __init__(self, seed: int = 0, size: int = 40):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.size = size
        self.t = 0
        self.occupancy = np.zeros((size, size))
        self.accessibility = np.ones((size, size))
        self.comm = np.ones((size, size))
        self.hazard = np.zeros((size, size))
        self.occupancy[12:20, 17:24] = 0.8
        self.accessibility[12:20, 17:24] = 0.25
        self.comm[25:36, 2:15] = 0.25
        self.survivors = [
            Survivor("S1", Pose2D(29, 8), 0.9),
            Survivor("S2", Pose2D(9, 31), 0.55, acoustic=0.9, visibility=0.3),
        ]
        self.hazards = [Hazard("fire", Pose2D(24, 27), 4, 0.65, 0.02)]

    def step(self) -> None:
        self.t += 1
        yy, xx = np.mgrid[: self.size, : self.size]
        self.hazard *= 0.98
        for hazard in self.hazards:
            hazard.radius += hazard.growth
            distance = np.hypot(xx - hazard.pose.x, yy - hazard.pose.y)
            self.hazard = np.maximum(
                self.hazard,
                np.clip(
                    hazard.severity * (1.0 - distance / max(hazard.radius, 1e-6)),
                    0.0,
                    1.0,
                ),
            )
        if self.t == 10:
            self.accessibility[8:14, 26:31] = 0.15


class SensorSuite:
    BASE = {
        "thermal": (0.88, 0.12),
        "rgb": (0.80, 0.15),
        "acoustic": (0.78, 0.18),
        "radar": (0.82, 0.14),
        "environmental": (0.90, 0.10),
        "depth": (0.86, 0.12),
    }

    def __init__(self, world: DisasterWorld):
        self.world = world

    def reliability(
        self,
        modality: str,
        pose: Pose2D,
        timestamp: float,
        failed: bool = False,
    ) -> tuple[float, ReliabilityState]:
        del timestamp
        if failed:
            return 0.0, ReliabilityState.FAILED
        quality = self.BASE[modality][0]
        hazard = self.world.hazard[
            int(np.clip(pose.y, 0, self.world.size - 1)),
            int(np.clip(pose.x, 0, self.world.size - 1)),
        ]
        if modality in {"rgb", "thermal"}:
            quality -= 0.45 * hazard
        if modality == "acoustic":
            quality -= 0.15 * hazard
        quality = float(np.clip(quality, 0.0, 1.0))
        if quality >= 0.75:
            state = ReliabilityState.RELIABLE
        elif quality >= 0.45:
            state = ReliabilityState.DEGRADED
        else:
            state = ReliabilityState.UNCERTAIN
        return quality, state

    def observe(
        self,
        agent: Agent,
        survivor: Survivor,
        modality: str,
        timestamp: float,
    ) -> Observation:
        distance = math.hypot(
            agent.pose.x - survivor.pose.x,
            agent.pose.y - survivor.pose.y,
        )
        reliability, _ = self.reliability(
            modality,
            agent.pose,
            timestamp,
            agent.failed,
        )
        signal = {
            "thermal": survivor.thermal,
            "rgb": survivor.visibility,
            "acoustic": survivor.acoustic,
            "radar": survivor.motion,
            "environmental": 0.35,
            "depth": 0.7,
        }[modality]
        noise = self.world.rng.normal(
            0.0,
            self.BASE[modality][1] + (1.0 - reliability) * 0.25,
        )
        score = float(
            np.clip(signal * math.exp(-distance / 16.0) + noise, 0.0, 1.0)
        )
        if modality == "thermal":
            score = float(
                np.clip(
                    score
                    + 0.5
                    * self.world.hazard[int(agent.pose.y), int(agent.pose.x)],
                    0.0,
                    1.0,
                )
            )
        observation_id = str(uuid.uuid4())
        return Observation(
            modality,
            score,
            float(np.clip(1.0 - abs(noise), 0.0, 1.0)),
            reliability,
            float(timestamp),
            survivor.pose,
            1.5 + (1.0 - reliability) * 3.0,
            4.0,
            Provenance(
                observation_id,
                agent.agent_id,
                f"{agent.agent_id}:{modality}",
            ),
            {"distance": distance, "signal_quality": reliability},
        )


class TemporalBuffer:
    def __init__(self, window: float = 3.0):
        self.window = window
        self.items: list[Observation] = []

    def add(self, observation: Observation) -> None:
        self.items.append(observation)
        self.items.sort(key=lambda item: item.timestamp)

    def aligned(self, now: float) -> list[Observation]:
        return [
            observation
            for observation in self.items
            if not observation.stale(now)
            and abs(now - observation.timestamp) <= self.window
        ]
