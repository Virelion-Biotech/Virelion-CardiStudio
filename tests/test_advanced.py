import numpy as np
import pytest
from cardistudio import (
    full_factorial, correlated_normals, TrajectorySpec, exponential_recovery,
    ConstraintEngine, range_constraint, cohens_d, approximate_two_sample_n,
)

def test_factorial_design():
    d = full_factorial({"injury": ["sham", "MI"], "zone": ["remote", "IZ"]}, replicates=3, blocks=2)
    assert d.n_factorial_cells == 4
    assert d.n_runs == 24
    assert len(d.rows) == 24

def test_correlated_normals_reproducible():
    corr = [[1,.8],[.8,1]]
    a = correlated_normals(1000, [0,0], [1,1], corr, seed=9)
    b = correlated_normals(1000, [0,0], [1,1], corr, seed=9)
    assert np.array_equal(a,b)
    assert np.corrcoef(a.T)[0,1] > .7

def test_trajectory():
    s = TrajectorySpec((0,1,7), 1, 0, .5)
    x = exponential_recovery(s, 10)
    assert x.shape == (10,3)
    assert x[0,0] > x[0,-1]

def test_constraints():
    r = ConstraintEngine([range_constraint("age", "age", 0, 100)]).validate([{"age": 50},{"age": 120}])
    assert not r.valid and len(r.violations) == 1

def test_power():
    d = cohens_d(1, 0, 1, 1)
    assert d == pytest.approx(1)
    assert approximate_two_sample_n(0.5) > 1
