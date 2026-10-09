from __future__ import annotations

import math
from statistics import NormalDist


def cohens_d(mean_a: float, mean_b: float, sd_a: float, sd_b: float) -> float:
    if not all(math.isfinite(v) for v in (mean_a, mean_b, sd_a, sd_b)):
        raise ValueError("Means and SDs must be finite")
    if sd_a <= 0 or sd_b <= 0:
        raise ValueError("SDs must be > 0")
    pooled = math.hypot(sd_a, sd_b) / math.sqrt(2)
    result = mean_a / pooled - mean_b / pooled
    if not math.isfinite(result):
        raise ValueError("Effect size exceeds floating-point range")
    return result


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
    if not all(math.isfinite(v) for v in (effect_size, alpha, power, icc)):
        raise ValueError("Power planning parameters must be finite")
    if effect_size <= 0 or not 0 < alpha < 1 or not alpha < power < 1:
        raise ValueError("effect_size > 0 and alpha/power must be in (0,1)")
    if type(cluster_size) is not int or cluster_size < 1 or not 0 <= icc < 1:
        raise ValueError("cluster_size must be >= 1 and ICC must be in [0,1)")
    tail = alpha / (2 if two_sided else 1)
    if tail == 0:
        raise ValueError("alpha is too small for floating-point planning")
    z_alpha = -NormalDist().inv_cdf(tail)
    z_power = NormalDist().inv_cdf(power)
    try:
        independent_n = 2 * ((z_alpha + z_power) / effect_size) ** 2
    except OverflowError as exc:
        raise ValueError("Requested sample size exceeds floating-point range") from exc
    design_effect = 1 + (cluster_size - 1) * icc
    inflated = independent_n * design_effect
    if not math.isfinite(inflated):
        raise ValueError("Requested sample size exceeds floating-point range")
    return max(1, math.ceil(inflated))


def simulation_power(simulate_trial, test_trial, *, repetitions=1000, seed=0):
    """Monte Carlo rejection rate for a caller-defined generative and test model.

    simulate_trial(rng) must implement the planned hierarchy/missingness/effects;
    test_trial(trial) must return a boolean rejection decision. This function
    does not establish adequacy of those models or clinical power.
    """
    import numpy as np

    if type(repetitions) is not int or repetitions < 2 or type(seed) is not int or seed < 0:
        raise ValueError("Require >=2 repetitions and a nonnegative integer seed")
    rng = np.random.default_rng(seed)
    rejections = 0
    for _ in range(repetitions):
        decision = test_trial(simulate_trial(rng))
        if not isinstance(decision, (bool, np.bool_)):
            raise ValueError("The trial test must return a boolean decision")
        rejections += int(decision)
    rate = rejections / repetitions
    # Wilson interval for Monte Carlo sampling error, including boundary rates.
    z = 1.959963984540054
    denom = 1 + z * z / repetitions
    center = (rate + z * z / (2 * repetitions)) / denom
    half = z * math.sqrt(rate * (1 - rate) / repetitions + z * z / (4 * repetitions**2)) / denom
    return {
        "rejection_rate": rate,
        "monte_carlo_interval": [center - half, center + half],
        "repetitions": repetitions,
        "rejections": rejections,
        "seed": seed,
        "scope": "conditional on supplied generative model and test; not external validation",
    }
