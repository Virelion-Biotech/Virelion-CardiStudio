import pytest
from cardistudio.presets import cardiac_mi_vs_sham
from cardistudio.population import PopulationBuilder
from cardistudio.validation import validate_challenge, validate_population

def test_demo_spec_valid():
    r = validate_challenge(cardiac_mi_vs_sham(100, 7)); assert r.valid

def test_reproducible_generation():
    s = cardiac_mi_vs_sham(100, 7)
    assert PopulationBuilder(s).build().rows == PopulationBuilder(s).build().rows

def test_group_counts_and_unique_ids():
    s = cardiac_mi_vs_sham(101, 9); p = PopulationBuilder(s).build(); r = validate_population(p.rows, s)
    assert r.valid; assert len({x["population_id"] for x in p.rows}) == 101

def test_invalid_group_total():
    s = cardiac_mi_vs_sham(100, 1); s.population.groups["mi"] += 1
    assert not validate_challenge(s).valid

def test_fingerprint_changes_with_spec():
    a = cardiac_mi_vs_sham(100, 1); b = cardiac_mi_vs_sham(100, 2)
    assert a.fingerprint() != b.fingerprint()
