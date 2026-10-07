import json

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from cardistudio import ChallengeSpec, FeatureSpec, PopulationBuilder, PopulationSpec
from cardistudio.cli import main
from cardistudio.constraints import declarative_constraint
from cardistudio.correlations import validate_correlation
from cardistudio.io import cardi_bridge_envelope, load_population, save_population
from cardistudio.serialization import strict_loads
from cardistudio.trajectory import TrajectorySpec, exponential_recovery, logistic_transition
from cardistudio.validation import validate_challenge, validate_population


def spec(feature):
    return ChallengeSpec(
        "contract", population=PopulationSpec(n=20, groups={"a": 10, "b": 10}), features=[feature]
    )


@pytest.mark.parametrize(
    "feature",
    [
        FeatureSpec("x", "continuous", "uniform", {"low": 2, "high": 1}),
        FeatureSpec("x", "continuous", "lognormal", {"sigma": 0}),
        FeatureSpec("x", "continuous", "lognormal", max_value=0),
        FeatureSpec("x", "continuous", min_value=1, max_value=1),
        FeatureSpec("x", "integer", min_value=0.1, max_value=0.9),
        FeatureSpec("x", "binary", "bernoulli", {"prob": 2}),
        FeatureSpec("x", "binary", "bernoulli", {"prob": 0.5}, effects={"a": {"shift": 1}}),
        FeatureSpec("x", "categorical", "categorical", {"categories": ["a", "a"]}),
        FeatureSpec(
            "x",
            "categorical",
            "categorical",
            {"categories": ["a", "b"], "probabilities": [0.2, 0.2]},
        ),
        FeatureSpec(
            "x", "categorical", "categorical", {"categories": ["a", "b"], "probabilities": [-1, 2]}
        ),
        FeatureSpec("x", "integer", "constant", {"value": 1.5}),
        FeatureSpec("x", "integer", "constant", {"value": 3}, max_value=2),
        FeatureSpec("x", "binary", "constant", {"value": 2}),
        FeatureSpec("x", "continuous", "constant", {"value": None}),
        FeatureSpec("x", "categorical", "constant", {"value": "a"}, effects={"a": {"shift": 1}}),
    ],
)
def test_invalid_distribution_contracts(feature):
    assert not validate_challenge(spec(feature)).valid
    with pytest.raises(ValueError):
        PopulationBuilder(spec(feature))


@pytest.mark.parametrize(
    "matrix",
    [
        [],
        [[1, float("nan")], [float("nan"), 1]],
        [[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]],
        [[1, 0], [0, 2]],
        [[1, 0, 0], [0, 1, 0]],
    ],
)
def test_invalid_correlations(matrix):
    with pytest.raises(ValueError):
        validate_correlation(matrix)


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}'])
def test_noncanonical_json_is_rejected(text):
    with pytest.raises(ValueError):
        strict_loads(text)


@pytest.mark.parametrize(
    "expr", ['__import__("os")', "x.__class__", "x[0]", "1e999 > 0", "1j == 1j", "x + "]
)
def test_constraint_expressions_fail_closed(expr):
    with pytest.raises(ValueError):
        declarative_constraint({"name": "bad", "type": "relation", "expr": expr})


def test_constraint_arithmetic_rejects_undefined_or_expensive_results():
    for expr in ['"x" * 10000000 == "x"', "x ** 1000000 > 0", "x * x > 0"]:
        constraint = declarative_constraint({"name": "bad", "type": "relation", "expr": expr})
        with pytest.raises((ValueError, OverflowError)):
            constraint.predicate({"x": 1e308})


@pytest.mark.parametrize(
    "field,value",
    [
        ("subject_id", ""),
        ("section_id", ""),
        ("biological_replicate", 0),
        ("synthetic", False),
        ("condition", "missing"),
        ("x", "bad"),
    ],
)
def test_population_contract_tampering(field, value):
    challenge = spec(FeatureSpec("x", "continuous"))
    rows = PopulationBuilder(challenge).build().rows
    rows[0][field] = value
    assert not validate_population(rows, challenge).valid


@settings(max_examples=30, deadline=None)
@given(
    st.floats(min_value=-10, max_value=10, allow_nan=False),
    st.floats(min_value=0.1, max_value=5, allow_nan=False),
    st.integers(0, 100000),
)
def test_bounded_sampler_property(mean, sd, seed):
    challenge = spec(
        FeatureSpec(
            "x", "continuous", "normal", {"mean": mean, "sd": sd}, min_value=-1, max_value=1
        )
    )
    challenge.population.seed = seed
    population = PopulationBuilder(challenge).build()
    assert all(-1 <= r["x"] <= 1 for r in population.rows)
    assert population.rows == PopulationBuilder(challenge).build().rows


def test_categorical_scalar_types_and_counts_are_preserved():
    challenge = spec(FeatureSpec("x", "categorical", "categorical", {"categories": [1, "1"]}))
    population = PopulationBuilder(challenge).build()
    assert {type(row["x"]) for row in population.rows} == {int, str}
    counts = population.provenance["ground_truth"]["comparisons"]["b_vs_a"]["x"]
    assert sum(counts["sample_counts_ref"].values()) == 10
    assert set(counts["sample_counts_ref"]) <= {"1", '"1"'}
    json.dumps(population.provenance, allow_nan=False)


def test_verified_io_requires_sidecar_and_preserves_existing_output(tmp_path):
    challenge = spec(FeatureSpec("x", "continuous"))
    population = PopulationBuilder(challenge).build()
    path = tmp_path / "population.jsonl"
    save_population(population, path)
    original = path.read_bytes()
    population.rows[0]["x"] += 1
    with pytest.raises(ValueError):
        save_population(population, path)
    assert path.read_bytes() == original
    path.with_suffix(".jsonl.provenance.json").unlink()
    with pytest.raises(ValueError, match="sidecar"):
        load_population(path)
    assert len(load_population(path, verify_provenance=False)) == 20


def test_export_rejects_wrong_challenge_and_empty_consumer():
    challenge = spec(FeatureSpec("x", "continuous"))
    population = PopulationBuilder(challenge).build()
    with pytest.raises(ValueError):
        cardi_bridge_envelope(challenge, population, " ")
    challenge.name = "different"
    with pytest.raises(ValueError, match="supplied challenge"):
        cardi_bridge_envelope(challenge, population)


def test_cli_invalid_input_is_actionable(tmp_path, capsys):
    assert main(["demo", "--n", "1", "--output", str(tmp_path)]) == 2
    assert "at least 2" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_stable_trajectories_and_large_rate_variability():
    transition = logistic_transition([-1e308, 1e308], 0, 1, 0, 1)
    assert np.array_equal(transition, [0, 1])
    trajectory = TrajectorySpec((0, 1, 10), 1, 0, rate=0.1, subject_rate_sd=10)
    values = exponential_recovery(trajectory, 1000)
    assert np.all(np.diff(values, axis=1) < 0)
    assert not np.any(values[:, -1] == values[:, 0])
    with pytest.raises(ValueError):
        exponential_recovery(TrajectorySpec((0, 0), 1, 0), 2)
