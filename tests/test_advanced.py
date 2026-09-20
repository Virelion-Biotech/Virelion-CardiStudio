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
from cardistudio.constraints import declarative_constraint, expression_names


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


def test_trajectory():
    spec = TrajectorySpec((0, 1, 7), 1, 0, 0.5, subject_intercept_sd=0.1, subject_rate_sd=0.05)
    values = exponential_recovery(spec, 10)
    assert values.shape == (10, 3)
    assert np.isfinite(values).all()


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


def test_power_icc_inflation():
    independent = approximate_two_sample_n(0.5)
    clustered = approximate_two_sample_n(0.5, cluster_size=10, icc=0.4)
    assert clustered > independent
    assert clustered == 289


def test_power():
    assert cohens_d(1, 0, 1, 1) == pytest.approx(1)
    assert approximate_two_sample_n(0.5) > 1
