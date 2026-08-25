from dataclasses import dataclass, field
from typing import Any
from .models import ChallengeSpec

@dataclass
class ValidationReport:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    def raise_if_invalid(self):
        if not self.valid: raise ValueError("; ".join(self.errors))

def validate_challenge(spec: ChallengeSpec) -> ValidationReport:
    e, w = [], []
    if not spec.name.strip(): e.append("Challenge name is required")
    if spec.population.n < 1: e.append("Population n must be >= 1")
    if sum(spec.population.groups.values()) != spec.population.n: e.append("Group counts must sum to n")
    if len(set(f.name for f in spec.features)) != len(spec.features): e.append("Feature names must be unique")
    for f in spec.features:
        if f.distribution == "categorical" and not f.params.get("categories"): e.append(f"{f.name}: categorical requires categories")
        if f.min_value is not None and f.max_value is not None and f.min_value > f.max_value: e.append(f"{f.name}: min_value > max_value")
    if spec.population.biological_replicates < 1: e.append("biological_replicates must be >= 1")
    return ValidationReport(not e, e, w, {"n_features": len(spec.features), "n_groups": len(spec.population.groups)})

def validate_population(rows: list[dict], spec: ChallengeSpec) -> ValidationReport:
    e, w = [], []
    if len(rows) != spec.population.n: e.append(f"Expected {spec.population.n} rows, got {len(rows)}")
    ids = [r.get("population_id") for r in rows]
    if len(ids) != len(set(ids)): e.append("population_id values are not unique")
    gf = spec.population.group_field
    observed = {}
    for r in rows: observed[r.get(gf)] = observed.get(r.get(gf), 0) + 1
    if observed != spec.population.groups: e.append(f"Group counts mismatch: {observed} != {spec.population.groups}")
    for f in spec.features:
        if any(f.name not in r for r in rows): e.append(f"Missing feature: {f.name}")
    return ValidationReport(not e, e, w, {"observed_groups": observed})
