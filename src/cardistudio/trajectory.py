from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy.special import expit
from scipy.stats import truncnorm
import math


@dataclass(frozen=True)
class TrajectorySpec:
    times: tuple[float, ...]
    baseline: float
    target: float
    rate: float = 0.2
    noise_sd: float = 0.0
    subject_intercept_sd: float = 0.0
    subject_rate_sd: float = 0.0

    def validate(self) -> None:
        if not all(
            math.isfinite(v)
            for v in (
                *self.times,
                self.baseline,
                self.target,
                self.rate,
                self.noise_sd,
                self.subject_intercept_sd,
                self.subject_rate_sd,
            )
        ):
            raise ValueError("Trajectory parameters must be finite")
        if not self.times:
            raise ValueError("times cannot be empty")
        if any(self.times[i] >= self.times[i + 1] for i in range(len(self.times) - 1)):
            raise ValueError("times must be sorted")
        if any(t < 0 for t in self.times):
            raise ValueError("Recovery times must be nonnegative")
        if self.rate <= 0:
            raise ValueError("rate must be > 0")
        if self.noise_sd < 0 or self.subject_intercept_sd < 0 or self.subject_rate_sd < 0:
            raise ValueError("trajectory SD parameters must be >= 0")


def exponential_recovery(spec: TrajectorySpec, n: int, seed: int = 42) -> np.ndarray:
    spec.validate()
    if type(n) is not int or n < 1:
        raise ValueError("n must be >= 1")

    rng = np.random.default_rng(seed)
    times = np.asarray(spec.times, dtype=float)
    intercepts = rng.normal(0, spec.subject_intercept_sd, n)
    rates = (
        truncnorm.rvs(
            -spec.rate / spec.subject_rate_sd,
            np.inf,
            loc=spec.rate,
            scale=spec.subject_rate_sd,
            size=n,
            random_state=rng,
        )
        if spec.subject_rate_sd
        else np.full(n, spec.rate)
    )
    values = np.empty((n, len(times)), dtype=float)
    for i in range(n):
        with np.errstate(over="ignore"):
            decay = np.exp(-rates[i] * times)
            values[i] = (1 - decay) * spec.target + decay * (spec.baseline + intercepts[i])
    if spec.noise_sd:
        values += rng.normal(0, spec.noise_sd, size=values.shape)
    if not np.isfinite(values).all():
        raise ValueError("Trajectory output overflowed; reduce parameter magnitudes")
    return values


def subject_exponential_long(
    subject_ids: Iterable[str], spec: TrajectorySpec, seed: int = 42
) -> list[dict[str, float | str]]:
    """Attach subject trajectories to repeated-measures long format."""
    ids = [str(value) for value in subject_ids]
    if any(not value.strip() for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("Subject identities must be nonempty and unique")
    values = exponential_recovery(spec, len(ids), seed)
    return [
        {"subject_id": subject_id, "time": float(time), "value": float(values[i, j])}
        for i, subject_id in enumerate(ids)
        for j, time in enumerate(spec.times)
    ]


def logistic_transition(
    times: list[float],
    low: float,
    high: float,
    midpoint: float,
    slope: float,
) -> np.ndarray:
    if not all(math.isfinite(v) for v in (*times, low, high, midpoint, slope)):
        raise ValueError("Logistic parameters must be finite")
    if slope <= 0:
        raise ValueError("slope must be > 0")
    values = np.asarray(times, dtype=float)
    with np.errstate(over="ignore"):
        weight = expit(slope * (values - midpoint))
    return (1 - weight) * low + weight * high
