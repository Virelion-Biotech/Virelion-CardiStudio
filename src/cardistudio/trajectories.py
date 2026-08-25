from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class TrajectoryPoint:
    subject_id: str
    time: float
    value: float


def logistic_trajectory(
    subject_ids: Iterable[str],
    times: Iterable[float],
    baseline: float,
    asymptote: float,
    rate: float,
    midpoint: float = 0.0,
) -> list[TrajectoryPoint]:
    """Generate deterministic logistic recovery/progression trajectories."""
    if rate <= 0:
        raise ValueError("rate must be positive")
    ids = list(subject_ids)
    ts = list(times)
    if not ids or not ts:
        return []
    points: list[TrajectoryPoint] = []
    for sid in ids:
        for t in ts:
            value = baseline + (asymptote - baseline) / (1.0 + math.exp(-rate * (t - midpoint)))
            points.append(TrajectoryPoint(str(sid), float(t), value))
    return points


def exponential_recovery(
    subject_ids: Iterable[str],
    times: Iterable[float],
    baseline: float,
    asymptote: float,
    rate: float,
) -> list[TrajectoryPoint]:
    """Generate monotonic exponential recovery/progression trajectories."""
    if rate <= 0:
        raise ValueError("rate must be positive")
    points: list[TrajectoryPoint] = []
    for sid in subject_ids:
        for t in times:
            t = float(t)
            value = asymptote + (baseline - asymptote) * math.exp(-rate * max(t, 0.0))
            points.append(TrajectoryPoint(str(sid), t, value))
    return points
