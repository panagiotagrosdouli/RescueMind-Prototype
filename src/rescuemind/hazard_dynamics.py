"""Deterministic grid-based hazard propagation for synthetic experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import hypot


class HazardKind(str, Enum):
    FIRE = "fire"
    SMOKE = "smoke"
    TOXIC_GAS = "toxic_gas"


@dataclass(frozen=True)
class HazardCell:
    fire: float = 0.0
    smoke: float = 0.0
    toxic_gas: float = 0.0
    blocked: bool = False
    flammability: float = 1.0

    def __post_init__(self) -> None:
        for value in (self.fire, self.smoke, self.toxic_gas, self.flammability):
            if not 0.0 <= value <= 1.0:
                raise ValueError("hazard values must be within [0, 1]")


@dataclass(frozen=True)
class HazardSnapshot:
    time: float
    width: int
    height: int
    cells: tuple[HazardCell, ...]

    def cell(self, x: int, y: int) -> HazardCell:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("cell outside hazard grid")
        return self.cells[y * self.width + x]


@dataclass(frozen=True)
class HazardParameters:
    fire_spread: float = 0.28
    fire_decay: float = 0.03
    smoke_diffusion: float = 0.22
    smoke_decay: float = 0.05
    gas_diffusion: float = 0.16
    gas_decay: float = 0.025
    smoke_generation: float = 0.20
    wind_x: float = 0.0
    wind_y: float = 0.0
    wind_strength: float = 0.35

    def __post_init__(self) -> None:
        bounded = (
            self.fire_spread,
            self.fire_decay,
            self.smoke_diffusion,
            self.smoke_decay,
            self.gas_diffusion,
            self.gas_decay,
            self.smoke_generation,
            self.wind_strength,
        )
        if any(not 0.0 <= value <= 1.0 for value in bounded):
            raise ValueError("rate parameters must be within [0, 1]")


class HazardPropagationModel:
    """Synchronous, deterministic finite-grid hazard model."""

    def __init__(
        self,
        width: int,
        height: int,
        *,
        parameters: HazardParameters | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("grid dimensions must be positive")
        self.width = width
        self.height = height
        self.parameters = parameters or HazardParameters()
        self._cells = [HazardCell() for _ in range(width * height)]
        self.time = 0.0

    def set_cell(self, x: int, y: int, cell: HazardCell) -> None:
        self._cells[self._index(x, y)] = cell

    def snapshot(self) -> HazardSnapshot:
        return HazardSnapshot(self.time, self.width, self.height, tuple(self._cells))

    def step(self, dt: float = 1.0) -> HazardSnapshot:
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        previous = tuple(self._cells)
        updated: list[HazardCell] = []
        for y in range(self.height):
            for x in range(self.width):
                current = previous[self._index(x, y)]
                if current.blocked:
                    updated.append(current)
                    continue
                neighbours = self._neighbours(x, y)
                fire_in = self._incoming(previous, x, y, neighbours, "fire")
                smoke_in = self._incoming(previous, x, y, neighbours, "smoke")
                gas_in = self._incoming(previous, x, y, neighbours, "toxic_gas")
                p = self.parameters
                fire = current.fire * (1.0 - p.fire_decay * dt)
                fire += p.fire_spread * current.flammability * fire_in * dt
                smoke = current.smoke * (1.0 - p.smoke_decay * dt)
                smoke += p.smoke_diffusion * smoke_in * dt
                smoke += p.smoke_generation * current.fire * dt
                gas = current.toxic_gas * (1.0 - p.gas_decay * dt)
                gas += p.gas_diffusion * gas_in * dt
                updated.append(
                    HazardCell(
                        fire=self._clamp(fire),
                        smoke=self._clamp(smoke),
                        toxic_gas=self._clamp(gas),
                        blocked=False,
                        flammability=current.flammability,
                    )
                )
        self._cells = updated
        self.time += dt
        return self.snapshot()

    def forecast(self, steps: int, dt: float = 1.0) -> tuple[HazardSnapshot, ...]:
        if steps < 0:
            raise ValueError("steps must be non-negative")
        saved_cells = list(self._cells)
        saved_time = self.time
        snapshots = tuple(self.step(dt) for _ in range(steps))
        self._cells = saved_cells
        self.time = saved_time
        return snapshots

    def risk_at(
        self,
        x: int,
        y: int,
        *,
        fire_weight: float = 0.5,
        smoke_weight: float = 0.3,
        gas_weight: float = 0.2,
    ) -> float:
        weights = fire_weight + smoke_weight + gas_weight
        if weights <= 0.0:
            raise ValueError("risk weights must sum to a positive value")
        cell = self._cells[self._index(x, y)]
        return self._clamp(
            (fire_weight * cell.fire + smoke_weight * cell.smoke + gas_weight * cell.toxic_gas)
            / weights
        )

    def unsafe_cells(self, threshold: float = 0.5) -> tuple[tuple[int, int], ...]:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be within [0, 1]")
        return tuple(
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.risk_at(x, y) >= threshold
        )

    def _incoming(
        self,
        cells: tuple[HazardCell, ...],
        x: int,
        y: int,
        neighbours: tuple[tuple[int, int], ...],
        field: str,
    ) -> float:
        total = 0.0
        normalizer = 0.0
        for nx, ny in neighbours:
            neighbour = cells[self._index(nx, ny)]
            if neighbour.blocked:
                continue
            weight = self._wind_weight(nx, ny, x, y)
            total += getattr(neighbour, field) * weight
            normalizer += weight
        return total / normalizer if normalizer else 0.0

    def _wind_weight(self, source_x: int, source_y: int, target_x: int, target_y: int) -> float:
        p = self.parameters
        wind_norm = hypot(p.wind_x, p.wind_y)
        if wind_norm == 0.0:
            return 1.0
        dx = target_x - source_x
        dy = target_y - source_y
        alignment = (dx * p.wind_x + dy * p.wind_y) / wind_norm
        return max(0.05, 1.0 + p.wind_strength * alignment)

    def _neighbours(self, x: int, y: int) -> tuple[tuple[int, int], ...]:
        candidates = ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
        return tuple(
            (nx, ny)
            for nx, ny in candidates
            if 0 <= nx < self.width and 0 <= ny < self.height
        )

    def _index(self, x: int, y: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("cell outside hazard grid")
        return y * self.width + x

    @staticmethod
    def _clamp(value: float) -> float:
        return min(1.0, max(0.0, value))
