from __future__ import annotations

import math
from statistics import NormalDist


def cohens_d(mean_a: float, mean_b: float, sd_a: float, sd_b: float) -> float:
    if sd_a <= 0 or sd_b <= 0:
        raise ValueError("SDs must be > 0")
    pooled = math.sqrt((sd_a**2 + sd_b**2) / 2)
    return (mean_a - mean_b) / pooled


def approximate_two_sample_n(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
    two_sided: bool = True,
    cluster_size: int = 1,
    icc: float = 0.0,
) -> int:
    """Approximate observations per arm, inflated for clustered observations.

    cluster_size is the expected number of observations per biological
    replicate/subject. The design effect is 1 + (m - 1) * ICC.
    """
    if effect_size <= 0 or not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("effect_size > 0 and alpha/power must be in (0,1)")
    if cluster_size < 1 or not 0 <= icc < 1:
        raise ValueError("cluster_size must be >= 1 and ICC must be in [0,1)")
    z_alpha = NormalDist().inv_cdf(1 - alpha / (2 if two_sided else 1))
    z_power = NormalDist().inv_cdf(power)
    independent_n = 2 * ((z_alpha + z_power) / effect_size) ** 2
    design_effect = 1 + (cluster_size - 1) * icc
    return math.ceil(independent_n * design_effect)
