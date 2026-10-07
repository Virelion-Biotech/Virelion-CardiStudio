from __future__ import annotations

import json

import numpy as np
import pytest
from scipy.stats import norm, truncnorm

from cardistudio import ChallengeSpec, FeatureSpec, PopulationBuilder, PopulationSpec
from cardistudio.constraints import declarative_constraint
from cardistudio.design import ExperimentalDesign, Factor
from cardistudio.io import load_challenge, load_population, save_population
from cardistudio.models import migrate_challenge_dict
from cardistudio.power import approximate_two_sample_n
from cardistudio.trajectory import TrajectorySpec, exponential_recovery
from cardistudio.validation import validate_challenge, validate_population


def specification(feature=None, n=100):
    return ChallengeSpec(
        "regression",
        population=PopulationSpec(n=n, groups={"a": n}),
        features=[feature or FeatureSpec("x", "continuous")],
    )


def test_bounded_normal_preserves_uniform_quantiles():
    feature = FeatureSpec(
        "x", "continuous", "normal", {"mean": 0, "sd": 1}, min_value=-1, max_value=1
    )
    builder = PopulationBuilder(specification(feature))
    quantiles = np.array([0.01, 0.25, 0.5, 0.75, 0.99])
    values, _ = builder._sample_continuous(feature, norm.ppf(quantiles), "a")
    assert np.allclose(truncnorm.cdf(values, -1, 1), quantiles, atol=1e-12)


def test_bounded_lognormal_preserves_uniform_quantiles():
    feature = FeatureSpec(
        "x",
        "continuous",
        "lognormal",
        {"mean": 0, "sigma": 1},
        min_value=np.exp(-1),
        max_value=np.exp(1),
    )
    builder = PopulationBuilder(specification(feature))
    quantiles = np.array([0.01, 0.25, 0.5, 0.75, 0.99])
    values, _ = builder._sample_continuous(feature, norm.ppf(quantiles), "a")
    assert np.allclose(truncnorm.cdf(np.log(values), -1, 1), quantiles, atol=1e-12)


def test_extreme_tail_truncation_has_finite_nonconstant_draws():
    feature = FeatureSpec(
        "x", "continuous", "normal", {"mean": 0, "sd": 1}, min_value=20, max_value=21
    )
    values, _ = PopulationBuilder(specification(feature))._sample_continuous(
        feature, np.array([-1.0, 0.0, 1.0]), "a"
    )
    assert np.isfinite(values).all() and np.ptp(values) > 0
    assert values[1] == pytest.approx(truncnorm.ppf(0.5, 20, 21))


def test_zero_lognormal_lower_bound_is_valid():
    feature = FeatureSpec("x", "continuous", "lognormal", {"sigma": 0.2}, min_value=0)
    assert all(row["x"] > 0 for row in PopulationBuilder(specification(feature)).build().rows)


def test_integer_rounding_respects_requested_bounds():
    feature = FeatureSpec(
        "x", "integer", "normal", {"mean": 1, "sd": 1}, min_value=0.6, max_value=1.6
    )
    rows = PopulationBuilder(specification(feature, 1000)).build().rows
    assert {row["x"] for row in rows} == {1}


@pytest.mark.parametrize(
    "feature",
    [
        FeatureSpec("synthetic", "continuous"),
        FeatureSpec("x", "continuous", "normal", {"sd": float("nan")}),
        FeatureSpec("x", "continuous", "constant", {"value": "not-numeric"}),
        FeatureSpec("x", "continuous", "normal", {"sd": -1}),
        FeatureSpec("x", "continuous", "normal", {"sdd": 1}),
    ],
)
def test_invalid_specs_rejected_before_sampling(feature):
    spec = specification(feature)
    assert not validate_challenge(spec).valid
    with pytest.raises(ValueError):
        PopulationBuilder(spec).build()


def test_zero_sized_group_supported_without_division_by_zero():
    spec = specification()
    spec.population.groups = {"empty": 0, "a": 100}
    assert len(PopulationBuilder(spec).build().rows) == 100


def test_constraint_implication_short_circuits_undefined_rhs():
    constraint = declarative_constraint(
        {
            "name": "safe",
            "type": "relation",
            "expr": "x != 0 implies 1 / x > 0",
            "severity": "error",
        }
    )
    assert constraint.predicate({"x": 0})


def test_constraint_syntax_errors_are_validation_errors():
    spec = specification()
    spec.constraints = [{"name": "broken", "type": "relation", "expr": "x >", "severity": "error"}]
    assert not validate_challenge(spec).valid


def test_build_is_repeatable_on_same_builder():
    spec = specification()
    spec.population.biological_replicates = 10
    builder = PopulationBuilder(spec)
    assert builder.build().rows == builder.build().rows


def test_builder_detaches_mutable_source_spec():
    spec = specification()
    builder = PopulationBuilder(spec)
    spec.features[0].name = "changed"
    assert "x" in builder.build().rows[0]


def test_population_validation_rejects_nan_and_missing_hierarchy():
    spec = specification()
    rows = PopulationBuilder(spec).build().rows
    rows[0]["x"] = float("nan")
    rows[0].pop("subject_id")
    assert not validate_population(rows, spec).valid


def test_population_tampering_detected_on_reload(tmp_path):
    population = PopulationBuilder(specification()).build()
    path = tmp_path / "population.jsonl"
    save_population(population, path)
    rows = path.read_text().splitlines()
    first = json.loads(rows[0])
    first["x"] = 1000
    rows[0] = json.dumps(first)
    path.write_text("\n".join(rows) + "\n")
    with pytest.raises(ValueError):
        load_population(path)


def test_challenge_duplicate_json_keys_rejected(tmp_path):
    raw = json.dumps(specification().to_dict())
    raw = raw.replace('"name": "regression"', '"name":"forged","name":"regression"')
    path = tmp_path / "challenge.json"
    path.write_text(raw)
    with pytest.raises(ValueError):
        load_challenge(path)


def test_unsupported_minor_version_cannot_be_downgraded():
    raw = specification().to_dict()
    raw["version"] = "1.999"
    with pytest.raises(ValueError):
        migrate_challenge_dict(raw)


def test_nonfinite_power_parameters_rejected():
    with pytest.raises(ValueError):
        approximate_two_sample_n(float("inf"))


def test_nonfinite_trajectory_parameters_rejected():
    with pytest.raises(ValueError):
        exponential_recovery(TrajectorySpec((0.0, 1.0), 1.0, 0.0, rate=float("nan")), 2)


def test_factor_names_cannot_overwrite_design_identity():
    with pytest.raises(ValueError):
        ExperimentalDesign([Factor("block", (1, 2))]).generate()
