"""Deterministic CPU verification against analytic distributions, not biological data."""

from __future__ import annotations

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.stats import kstest, norm, truncnorm

from cardistudio import ChallengeSpec, FeatureSpec, PopulationBuilder, PopulationSpec
from cardistudio.power import approximate_two_sample_n


def validate() -> dict:
    seeds = [3, 17, 91]
    results = []
    marginals = [
        (
            FeatureSpec("x", "continuous", "normal", {"mean": 2, "sd": 3}),
            lambda x: norm.cdf(x, loc=2, scale=3),
            "normal",
        ),
        (
            FeatureSpec(
                "x", "continuous", "normal", {"mean": 0, "sd": 1}, min_value=-1, max_value=1
            ),
            lambda x: truncnorm.cdf(x, -1, 1),
            "bounded_normal",
        ),
        (
            FeatureSpec(
                "x", "continuous", "normal", {"mean": 0, "sd": 1}, min_value=20, max_value=21
            ),
            lambda x: truncnorm.cdf(x, 20, 21),
            "extreme_tail_normal",
        ),
        (
            FeatureSpec(
                "x", "continuous", "uniform", {"low": 0, "high": 10}, min_value=2, max_value=7
            ),
            lambda x: (x - 2) / 5,
            "bounded_uniform",
        ),
        (
            FeatureSpec("x", "continuous", "lognormal", {"mean": 0.4, "sigma": 0.7}),
            lambda x: norm.cdf(np.log(x), loc=0.4, scale=0.7),
            "lognormal",
        ),
        (
            FeatureSpec(
                "x",
                "continuous",
                "lognormal",
                {"mean": 0, "sigma": 1},
                min_value=np.exp(-1),
                max_value=np.exp(1),
            ),
            lambda x: truncnorm.cdf(np.log(x), -1, 1),
            "bounded_lognormal",
        ),
    ]
    for feature, cdf, label in marginals:
        for seed in seeds:
            spec = ChallengeSpec(
                label,
                population=PopulationSpec(
                    n=4000, groups={"a": 4000}, biological_replicates=4000, seed=seed
                ),
                features=[feature],
            )
            rows = PopulationBuilder(spec).build().rows
            values = np.array([row["x"] for row in rows])
            statistic = float(kstest(cdf(values), "uniform").statistic)
            assert statistic < 0.035, (label, seed, statistic)
            results.append(
                {
                    "check": label,
                    "seed": seed,
                    "observations": 4000,
                    "ks_statistic": statistic,
                    "maximum": 0.035,
                }
            )
    for icc in (0.0, 0.35, 0.8):
        estimates = []
        correlations = []
        for seed in seeds:
            spec = ChallengeSpec(
                "hierarchy",
                population=PopulationSpec(
                    n=6000,
                    groups={"a": 6000},
                    biological_replicates=1000,
                    intraclass_correlation=icc,
                    copula_features=["x", "y"],
                    correlation=[[1, 0.65], [0.65, 1]],
                    seed=seed,
                ),
                features=[FeatureSpec("x", "continuous"), FeatureSpec("y", "continuous")],
            )
            rows = PopulationBuilder(spec).build().rows
            subjects = {}
            for row in rows:
                subjects.setdefault(row["subject_id"], []).append(row["x"])
            x = np.array(list(subjects.values()))
            m = x.shape[1]
            ms_between = m * np.var(x.mean(axis=1), ddof=1)
            ms_within = np.mean(np.var(x, axis=1, ddof=1))
            estimate = (ms_between - ms_within) / (ms_between + (m - 1) * ms_within)
            estimates.append(float(estimate))
            correlations.append(
                float(np.corrcoef([[r["x"] for r in rows], [r["y"] for r in rows]])[0, 1])
            )
        assert abs(np.mean(estimates) - icc) < 0.05, (icc, estimates)
        assert abs(np.mean(correlations) - 0.65) < 0.05, correlations
        results.append(
            {
                "check": "balanced_ANOVA_ICC_and_normal_correlation",
                "target_icc": icc,
                "seeds": seeds,
                "subjects_per_seed": 1000,
                "observations_per_subject": 6,
                "icc_estimates": estimates,
                "correlation_estimates": correlations,
                "target_correlation": 0.65,
                "maximum_mean_absolute_error": 0.05,
            }
        )
    # Monte Carlo z tests with known variance: independent, equal-sized groups.
    # This checks the planner's stated approximation, not t-tests or mixed models.
    rng = np.random.default_rng(117)
    trials = 100000
    n = approximate_two_sample_n(0.5)
    observed_z = rng.normal(0.5 / np.sqrt(2 / n), 1, trials)
    achieved = float(np.mean(np.abs(observed_z) > norm.ppf(0.975)))
    assert 0.79 < achieved < 0.82, achieved
    results.append(
        {
            "check": "normal_approximation_power",
            "seed": 117,
            "trials": trials,
            "effect_size": 0.5,
            "n_per_arm": n,
            "target_power": 0.8,
            "achieved_power": achieved,
        }
    )
    return {
        "scope": "Computational/statistical validation; no empirical biological validation",
        "package_version": version("virelion-cardistudio"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": version("scipy"),
        "passed": True,
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("validation/results.json"))
    args = parser.parse_args()
    report = validate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Passed {len(report['results'])} CPU scientific checks; saved {args.output}")
