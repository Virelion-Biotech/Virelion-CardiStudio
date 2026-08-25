from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import numpy as np

@dataclass(frozen=True)
class TrajectorySpec:
    times: tuple[float, ...]
    baseline: float
    target: float
    rate: float = 0.2
    noise_sd: float = 0.0

    def validate(self) -> None:
        if not self.times: raise ValueError("times cannot be empty")
        if any(self.times[i] > self.times[i+1] for i in range(len(self.times)-1)):
            raise ValueError("times must be sorted")
        if self.rate < 0: raise ValueError("rate must be >= 0")
        if self.noise_sd < 0: raise ValueError("noise_sd must be >= 0")


def exponential_recovery(spec: TrajectorySpec, n: int, seed: int = 42) -> np.ndarray:
    spec.validate()
    rng = np.random.default_rng(seed)
    t = np.asarray(spec.times, dtype=float)
    values = spec.target + (spec.baseline - spec.target) * np.exp(-spec.rate * t)
    if spec.noise_sd:
        values = values[None, :] + rng.normal(0, spec.noise_sd, size=(n, len(t)))
    else:
        values = np.broadcast_to(values, (n, len(t))).copy()
    return values


def logistic_transition(times: list[float], low: float, high: float, midpoint: float, slope: float) -> np.ndarray:
    if slope <= 0: raise ValueError("slope must be > 0")
    t = np.asarray(times, dtype=float)
    return low + (high-low)/(1+np.exp(-slope*(t-midpoint)))
