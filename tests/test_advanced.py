import sys

import numpy as np
import pytest

from cardistudio import (
    ConstraintEngine,
    TrajectorySpec,
    approximate_two_sample_n,
    cohens_d,
    correlated_normals,
    exponential_recovery,
    full_factorial,
)
from cardistudio.analysis import balance_report, summarize_population
from cardistudio.cli import main
from cardistudio.constraints import declarative_constraint, expression_names
from cardistudio.correlations import validate_correlation
from cardistudio.io import (
    export_cardi_bridge,
    load_population,
    save_challenge,
    save_population,
)
from cardistudio.models import ChallengeSpec, FeatureSpec, PopulationSpec
from cardistudio.population import PopulationBuilder
from cardistudio.presets import cardiac_mi_vs_sham
from cardistudio.trajectory import logistic_transition, subject_exponential_long


def test_factorial_design():
    design = full_factorial(
        {"injury": ["sham", "MI"], "zone": ["remote", "IZ"]},
        replicates=3,
        blocks=2,
    )
    assert design.n_factorial_cells == 4
    assert design.n_runs == 24
    assert len(design.rows) == 24
    assert len({row["cell_id"] for row in design.rows}) == 24


def test_correlated_normals_reproducible():
    corr = [[1, 0.8], [0.8, 1]]
    a = correlated_normals(1000, [0, 0], [1, 1], corr, seed=9)
    b = correlated_normals(1000, [0, 0], [1, 1], corr, seed=9)
    assert np.array_equal(a, b)
    assert np.corrcoef(a.T)[0, 1] > 0.7


def test_correlation_validation_errors():
    with pytest.raises(ValueError):
        validate_correlation([[1, 0.5], [0.1, 1]])
    with pytest.raises(ValueError):
        validate_correlation([[1, 1.2], [1.2, 1]])


def test_trajectory():
    spec = TrajectorySpec(
        (0, 1, 7), 1, 0, 0.5, subject_intercept_sd=0.1, subject_rate_sd=0.05
    )
    values = exponential_recovery(spec, 10)
    assert values.shape == (10, 3)
    assert np.isfinite(values).all()
    long = subject_exponential_long(["A", "B"], spec, seed=3)
    assert len(long) == 6
    assert {row["subject_id"] for row in long} == {"A", "B"}
    assert logistic_transition([0, 1], 0, 1, 0.5, 2).shape == (2,)


def test_constraints():
    report = ConstraintEngine([]).validate([{"age": 50}])
    assert report.valid


def test_constraint_dsl():
    expression = "ejection_fraction < 0.4 implies fibrosis_fraction > 0.15"
    assert expression_names(expression) == {"ejection_fraction", "fibrosis_fraction"}
    constraint = declarative_constraint(
        {"name": "coherence", "type": "relation", "expr": expression, "severity": "error"}
    )
    assert constraint.predicate({"ejection_fraction": 0.3, "fibrosis_fraction": 0.2})
    assert not constraint.predicate({"ejection_fraction": 0.3, "fibrosis_fraction": 0.1})
    with pytest.raises(ValueError):
        declarative_constraint(
            {"name": "bad", "type": "relation", "expr": "secret > 1", "severity": "error"},
            {"known"},
        )


def test_power_icc_inflation():
    independent = approximate_two_sample_n(0.5)
    clustered = approximate_two_sample_n(0.5, cluster_size=10, icc=0.4)
    assert clustered > independent
    assert clustered == 289


def test_power():
    assert cohens_d(1, 0, 1, 1) == pytest.approx(1)
    assert approximate_two_sample_n(0.5) > 1


def test_all_distribution_branches():
    spec = ChallengeSpec(
        name="all-distributions",
        population=PopulationSpec(n=100, groups={"a": 50, "b": 50}, seed=22),
        features=[
            FeatureSpec("u", "continuous", "uniform", {"low": 0, "high": 1}),
            FeatureSpec("ln", "continuous", "lognormal", {"mean": 0, "sigma": 0.2}),
            FeatureSpec("bin", "binary", "bernoulli", {"prob": 0.6}),
            FeatureSpec("cat", "categorical", "categorical", {"categories": ["x", "y"]}),
            FeatureSpec("const", "continuous", "constant", {"value": 3}),
        ],
    )
    population = PopulationBuilder(spec).build()
    assert len(population.rows) == 100
    assert set(row["cat"] for row in population.rows) <= {"x", "y"}


def test_population_io_and_analysis(tmp_path):
    spec = cardiac_mi_vs_sham(20, 8)
    population = PopulationBuilder(spec).build()
    assert summarize_population(population.rows)["n"] == 20
    report = balance_report(
        population.rows, "condition", ["ejection_fraction", "fibrosis_fraction"]
    )
    assert set(report["groups"]) == {"sham", "mi"}
    challenge_path = tmp_path / "challenge.json"
    population_path = tmp_path / "population.jsonl"
    save_challenge(spec, challenge_path)
    save_population(population, population_path)
    assert len(load_population(population_path)) == 20
    bridge = tmp_path / "bridge.json"
    export_cardi_bridge(spec, population, bridge)
    assert bridge.exists()


def test_cli_demo(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["cardistudio", "demo", "--n", "20", "--seed", "4", "--output", str(tmp_path)],
    )
    main()
    assert (tmp_path / "challenge.json").exists()
    assert (tmp_path / "population.jsonl").exists()
    assert (tmp_path / "population.csv").exists()
    assert (tmp_path / "cardi_bridge.json").exists()


def test_invalid_power_inputs():
    with pytest.raises(ValueError):
        approximate_two_sample_n(0.0)
    with pytest.raises(ValueError):
        approximate_two_sample_n(0.5, cluster_size=0)
