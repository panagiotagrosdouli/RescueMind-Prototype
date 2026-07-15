"""Bayesian survivor-belief tracking for synthetic RescueMind experiments."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import sqrt
from statistics import NormalDist


@dataclass(frozen=True)
class BayesianEvidence:
    """Reliability-weighted binary evidence for one survivor hypothesis."""

    evidence_id: str
    hypothesis_id: str
    supports_presence: bool
    reliability: float
    timestamp: float
    modality: str

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id must be non-empty")
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id must be non-empty")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be in [0, 1]")
        if self.timestamp < 0.0:
            raise ValueError("timestamp must be non-negative")


@dataclass(frozen=True)
class CredibleInterval:
    lower: float
    upper: float
    level: float


@dataclass(frozen=True)
class SurvivorBelief:
    """Beta-distributed belief over the probability of survivor presence."""

    hypothesis_id: str
    alpha: float = 1.0
    beta: float = 1.0
    last_update: float = 0.0
    evidence_ids: tuple[str, ...] = ()
    modalities: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id must be non-empty")
        if self.alpha <= 0.0 or self.beta <= 0.0:
            raise ValueError("alpha and beta must be positive")
        if self.last_update < 0.0:
            raise ValueError("last_update must be non-negative")

    @property
    def probability(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        total = self.alpha + self.beta
        return self.alpha * self.beta / (total * total * (total + 1.0))

    @property
    def evidence_strength(self) -> float:
        return self.alpha + self.beta - 2.0

    def interval(self, level: float = 0.95) -> CredibleInterval:
        """Return a bounded normal approximation to a Beta credible interval."""
        if not 0.0 < level < 1.0:
            raise ValueError("level must be in (0, 1)")
        z_score = NormalDist().inv_cdf(0.5 + level / 2.0)
        margin = z_score * sqrt(self.variance)
        return CredibleInterval(
            lower=max(0.0, self.probability - margin),
            upper=min(1.0, self.probability + margin),
            level=level,
        )


@dataclass(frozen=True)
class ReobservationDecision:
    hypothesis_id: str
    required: bool
    reason: str
    probability: float
    interval_width: float
    age: float


class BayesianWorldModel:
    """Maintain auditable Beta-Bernoulli beliefs for survivor hypotheses."""

    def __init__(
        self,
        *,
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
        decay_half_life: float = 300.0,
        uncertainty_threshold: float = 0.35,
        stale_after: float = 180.0,
    ) -> None:
        if prior_alpha <= 0.0 or prior_beta <= 0.0:
            raise ValueError("prior parameters must be positive")
        if decay_half_life <= 0.0:
            raise ValueError("decay_half_life must be positive")
        if not 0.0 < uncertainty_threshold <= 1.0:
            raise ValueError("uncertainty_threshold must be in (0, 1]")
        if stale_after <= 0.0:
            raise ValueError("stale_after must be positive")
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self.decay_half_life = decay_half_life
        self.uncertainty_threshold = uncertainty_threshold
        self.stale_after = stale_after
        self._beliefs: dict[str, SurvivorBelief] = {}
        self._seen_evidence: set[str] = set()

    def get(self, hypothesis_id: str) -> SurvivorBelief:
        return self._beliefs.get(
            hypothesis_id,
            SurvivorBelief(
                hypothesis_id=hypothesis_id,
                alpha=self.prior_alpha,
                beta=self.prior_beta,
            ),
        )

    def update(self, evidence: BayesianEvidence) -> SurvivorBelief:
        if evidence.evidence_id in self._seen_evidence:
            raise ValueError(f"duplicate evidence_id: {evidence.evidence_id}")
        current = self.get(evidence.hypothesis_id)
        if evidence.timestamp < current.last_update:
            raise ValueError("evidence timestamp must be monotonic per hypothesis")

        alpha_increment = evidence.reliability if evidence.supports_presence else 0.0
        beta_increment = evidence.reliability if not evidence.supports_presence else 0.0
        updated = SurvivorBelief(
            hypothesis_id=current.hypothesis_id,
            alpha=current.alpha + alpha_increment,
            beta=current.beta + beta_increment,
            last_update=evidence.timestamp,
            evidence_ids=current.evidence_ids + (evidence.evidence_id,),
            modalities=current.modalities | {evidence.modality},
        )
        self._beliefs[evidence.hypothesis_id] = updated
        self._seen_evidence.add(evidence.evidence_id)
        return updated

    def decayed(self, hypothesis_id: str, now: float) -> SurvivorBelief:
        current = self.get(hypothesis_id)
        if now < current.last_update:
            raise ValueError("now must not precede last_update")
        age = now - current.last_update
        retention = 0.5 ** (age / self.decay_half_life)
        alpha = self.prior_alpha + (current.alpha - self.prior_alpha) * retention
        beta = self.prior_beta + (current.beta - self.prior_beta) * retention
        return replace(current, alpha=alpha, beta=beta)

    def reobservation_decision(
        self,
        hypothesis_id: str,
        now: float,
        *,
        level: float = 0.95,
    ) -> ReobservationDecision:
        belief = self.decayed(hypothesis_id, now)
        interval = belief.interval(level)
        width = interval.upper - interval.lower
        age = now - belief.last_update
        if age >= self.stale_after:
            return ReobservationDecision(
                hypothesis_id, True, "stale belief", belief.probability, width, age
            )
        if width >= self.uncertainty_threshold:
            return ReobservationDecision(
                hypothesis_id,
                True,
                "credible interval too wide",
                belief.probability,
                width,
                age,
            )
        return ReobservationDecision(
            hypothesis_id, False, "belief sufficiently resolved", belief.probability, width, age
        )

    def ranked(self, now: float) -> tuple[SurvivorBelief, ...]:
        """Rank current hypotheses by decayed posterior probability."""
        beliefs = (self.decayed(hypothesis_id, now) for hypothesis_id in self._beliefs)
        return tuple(sorted(beliefs, key=lambda item: (-item.probability, item.hypothesis_id)))
