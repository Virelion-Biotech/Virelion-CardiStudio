import json

import numpy as np
import pytest

from cardistudio.io import load_challenge
from cardistudio.models import ChallengeSpec, FeatureSpec, PopulationSpec
from cardistudio.population import PopulationBuilder
from cardistudio.presets import cardiac_mi_vs_sham
from cardistudio.validation import validate_challenge, validate_population


def test_demo_spec_valid():
    report = validate_challenge(cardiac_mi_vs_sham(100, 7))
    assert report.valid, report.errors


def test_reproducible_generation():
    spec = cardiac_mi_vs_sham(100, 7)
    assert PopulationBuilder(spec).build().rows == PopulationBuilder(spec).build().rows


def test_group_counts_hierarchy_and_unique_ids():
    spec = cardiac_mi_vs_sham(101, 9)
    population = PopulationBuilder(spec).build()
    report = validate_population(population.rows, spec)
    assert report.valid, report.errors
    assert len({row["population_id"] for row in population.rows}) == 101
    assert len({row["subject_id"] for row in population.rows}) == 40
    assert all(row["synthetic"] is True for row in population.rows)


def test_effect_has_signal():
    population = PopulationBuilder(cardiac_mi_vs_sham(4000, 7)).build()
    sham = np.array(
        [row["ejection_fraction"] for row in population.rows if row["condition"] == "sham"]
    )
    mi = np.array(
        [row["ejection_fraction"] for row in population.rows if row["condition"] == "mi"]
    )
    assert mi.mean() < sham.mean() - 0.15
    fibrosis_sham = np.array(
        [row["fibrosis_fraction"] for row in population.rows if row["condition"] == "sham"]
    )
    fibrosis_mi = np.array(
        [row["fibrosis_fraction"] for row in population.rows if row["condition"] == "mi"]
    )
    assert fibrosis_mi.mean() > fibrosis_sham.mean() + 0.07


def test_copula_and_icc_structure():
    population = PopulationBuilder(cardiac_mi_vs_sham(6000, 19)).build()
    ef = np.array([row["ejection_fraction"] for row in population.rows])
    fib = np.array([row["fibrosis_fraction"] for row in population.rows])
    assert np.corrcoef(ef, fib)[0, 1] < -0.4

    by_subject: dict[str, list[float]] = {}
    for row in population.rows:
        by_subject.setdefault(row["subject_id"], []).append(row["ejection_fraction"])
    subject_means = np.array([np.mean(values) for values in by_subject.values()])
    between = np.var(subject_means, ddof=1)
    within = np.mean(
        [np.var(values, ddof=1) for values in by_subject.values() if len(values) > 1]
    )
    m = len(next(iter(by_subject.values())))
    empirical_icc = between / (between + within / m)
    assert empirical_icc > 0.15


def test_no_boundary_spike_from_truncation():
    spec = ChallengeSpec(
        name="bounded",
        population=PopulationSpec(n=5000, groups={"a": 2500, "b": 2500}, seed=11),
        features=[
            FeatureSpec(
                "x",
                "continuous",
                "normal",
                {"mean": 0, "sd": 3},
                min_value=-1,
                max_value=1,
            )
        ],
    )
    population = PopulationBuilder(spec).build()
    values = np.array([row["x"] for row in population.rows])
    boundary_fraction = np.mean((values == -1) | (values == 1))
    assert boundary_fraction < 0.01
    assert population.provenance["generation"]["truncation_rejection_rates"]["x"]["a"] > 0.5


def test_ground_truth_recorded():
    population = PopulationBuilder(cardiac_mi_vs_sham(1000, 2)).build()
    ground_truth = population.provenance["ground_truth"]
    assert ground_truth["feature_effects"]["ejection_fraction"]["mi"]["shift"] == pytest.approx(-0.22)
    assert "mi_vs_sham" in ground_truth["comparisons"]
    assert ground_truth["copula"]["target_correlation"][2][3] == pytest.approx(-0.55)


def test_constraints_enforced_during_generation():
    population = PopulationBuilder(cardiac_mi_vs_sham(500, 3)).build()
    assert all(
        not (row["ejection_fraction"] < 0.4 and row["fibrosis_fraction"] <= 0.15)
        for row in population.rows
    )
    assert population.provenance["generation"]["constraint_enforcement"] == "generative_resampling"


def test_unknown_keys_rejected_on_load(tmp_path):
    path = tmp_path / "bad.json"
    payload = cardiac_mi_vs_sham(10, 1).to_dict()
    payload["bogus"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema validation"):
        load_challenge(path)


def test_legacy_v10_migrates(tmp_path):
    path = tmp_path / "old.json"
    payload = cardiac_mi_vs_sham(10, 1).to_dict()
    payload["version"] = "1.0"
    for feature in payload["features"]:
        feature.pop("effects", None)
    for key in [
        "sections_per_subject",
        "intraclass_correlation",
        "subject_field",
        "section_field",
        "observation_field",
        "copula_features",
        "correlation",
    ]:
        payload["population"].pop(key, None)
    path.write_text(json.dumps(payload), encoding="utf-8")
    spec = load_challenge(path)
    assert spec.version == "1.1"


def test_fingerprint_changes_with_spec():
    a = cardiac_mi_vs_sham(100, 1)
    b = cardiac_mi_vs_sham(100, 2)
    assert a.fingerprint() != b.fingerprint()


def test_validation_error_paths():
    bad = cardiac_mi_vs_sham(20, 1)
    bad.population.groups["mi"] += 1
    assert not validate_challenge(bad).valid

    duplicate = cardiac_mi_vs_sham(20, 1)
    duplicate.features[1].name = duplicate.features[0].name
    assert not validate_challenge(duplicate).valid

    invalid_category = ChallengeSpec(
        name="bad-category",
        population=PopulationSpec(n=4, groups={"a": 2, "b": 2}),
        features=[
            FeatureSpec("cat", "categorical", "categorical", {"categories": []})
        ],
    )
    assert not validate_challenge(invalid_category).valid

    invalid_effect = cardiac_mi_vs_sham(20, 1)
    invalid_effect.features[2].effects["missing"] = {"shift": 1}
    assert not validate_challenge(invalid_effect).valid

    invalid_corr = cardiac_mi_vs_sham(20, 1)
    invalid_corr.population.correlation[0][1] = 2
    assert not validate_challenge(invalid_corr).valid
