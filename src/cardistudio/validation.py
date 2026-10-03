from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .correlations import validate_correlation
from .models import ChallengeSpec


@dataclass
class ValidationReport:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise ValueError("; ".join(self.errors))


def validate_challenge(spec: ChallengeSpec) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    if not spec.name.strip():
        errors.append("Challenge name is required")
    p = spec.population
    if p.n < 1:
        errors.append("Population n must be >= 1")
    if sum(p.groups.values()) != p.n:
        errors.append("Group counts must sum to n")
    if len(set(f.name for f in spec.features)) != len(spec.features):
        errors.append("Feature names must be unique")
    if p.biological_replicates < 1:
        errors.append("biological_replicates must be >= 1")
    if p.sections_per_subject < 1:
        errors.append("sections_per_subject must be >= 1")
    if not 0 <= p.intraclass_correlation < 1:
        errors.append("intraclass_correlation must be in [0,1)")
    feature_names = {f.name for f in spec.features}
    if p.correlation is not None:
        try:
            corr = validate_correlation(p.correlation)
            if len(p.copula_features) != corr.shape[0]:
                errors.append("copula_features length must match correlation matrix dimension")
            unknown = set(p.copula_features) - feature_names
            if unknown:
                errors.append(f"Unknown copula features: {sorted(unknown)}")
        except ValueError as exc:
            errors.append(str(exc))
    for feature in spec.features:
        if feature.distribution == "categorical" and not feature.params.get("categories"):
            errors.append(f"{feature.name}: categorical requires categories")
        if feature.min_value is not None and feature.max_value is not None:
            if feature.min_value > feature.max_value:
                errors.append(f"{feature.name}: min_value > max_value")
        for group, effect in feature.effects.items():
            if group not in p.groups:
                errors.append(f"{feature.name}: effect references unknown group {group!r}")
            if float(effect.get("scale", 1.0)) <= 0:
                errors.append(f"{feature.name}: effect scale must be > 0")
    if spec.constraints:
        from .constraints import declarative_constraint

        available = (
            {"population_id", p.group_field, p.subject_field, p.section_field,
             p.observation_field, "biological_replicate", "synthetic"}
            | feature_names
        )
        for constraint in spec.constraints:
            try:
                declarative_constraint(constraint, available)
            except ValueError as exc:
                errors.append(str(exc))
    return ValidationReport(
        not errors,
        errors,
        warnings,
        {"n_features": len(spec.features), "n_groups": len(p.groups)},
    )


def validate_population(rows: list[dict], spec: ChallengeSpec) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    if len(rows) != spec.population.n:
        errors.append(f"Expected {spec.population.n} rows, got {len(rows)}")
    ids = [r.get("population_id") for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("population_id values are not unique")
    group_field = spec.population.group_field
    observed: dict[str, int] = {}
    for row in rows:
        observed[str(row.get(group_field))] = observed.get(str(row.get(group_field)), 0) + 1
        if row.get("synthetic") is not True:
            errors.append("Every population row must include synthetic=true")
    if observed != spec.population.groups:
        errors.append(f"Group counts mismatch: {observed} != {spec.population.groups}")
    for feature in spec.features:
        if any(feature.name not in row for row in rows):
            errors.append(f"Missing feature: {feature.name}")
    return ValidationReport(not errors, errors, warnings, {"observed_groups": observed})
