from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np

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
        if not self.times: raise ValueError("times cannot be empty")
        if any(self.times[i] > self.times[i+1] for i in range(len(self.times)-1)):
            raise ValueError("times must be sorted")
        if self.rate <= 0: raise ValueError("rate must be > 0")
        if self.noise_sd < 0 or self.subject_intercept_sd < 0 or self.subject_rate_sd < 0:
            raise ValueError("trajectory SD parameters must be >= 0")


def exponential_recovery(spec: TrajectorySpec, n: int, seed: int = 42) -> np.ndarray:
    spec.validate()
    rng = np.random.default_rng(seed)
    t = np.asarray(spec.times, dtype=float)
    values = spec.target + (spec.baseline - spec.target) * np.exp(-spec.rate * t)
    intercepts = rng.normal(0, spec.subject_intercept_sd, n)
    rates = np.clip(rng.normal(spec.rate, spec.subject_rate_sd, n), 1e-12, None)
    values = np.empty((n, len(t)), dtype=float)
    for i in range(n):
        values[i] = spec.target + (spec.baseline + intercepts[i] - spec.target) * np.exp(-rates[i] * t)
    if spec.noise_sd:
        values += rng.normal(0, spec.noise_sd, size=values.shape)
    return values


def logistic_transition(times: list[float], low: float, high: float, midpoint: float, slope: float) -> np.ndarray:
    if slope <= 0: raise ValueError("slope must be > 0")
    t = np.asarray(times, dtype=float)
    return low + (high-low)/(1+np.exp(-slope*(t-midpoint)))


def subject_exponential_long(
    subject_ids: Iterable[str], spec: TrajectorySpec, seed: int = 42
) -> list[dict[str, float | str]]:
    """Attach subject trajectories to repeated-measures long format."""
    ids = [str(x) for x in subject_ids]
    values = exponential_recovery(spec, len(ids), seed)
    return [
        {"subject_id": sid, "time": float(t), "value": float(values[i, j])}
        for i, sid in enumerate(ids)
        for j, t in enumerate(spec.times)
    ]
