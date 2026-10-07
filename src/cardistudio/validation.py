from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from .correlations import validate_correlation
from .models import ChallengeSpec, FeatureSpec, PopulationSpec
from .serialization import canonical_json


@dataclass
class ValidationReport:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise ValueError("; ".join(self.errors))


def _number(value: Any) -> bool:
    try:
        return (
            not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
        )
    except OverflowError:
        return False


def validate_challenge(spec: ChallengeSpec) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    if (
        not isinstance(spec, ChallengeSpec)
        or not isinstance(spec.population, PopulationSpec)
        or any(not isinstance(feature, FeatureSpec) for feature in spec.features)
    ):
        return ValidationReport(False, ["Expected ChallengeSpec, PopulationSpec and FeatureSpec"])
    try:
        from .io import _validate_schema

        canonical_json(spec.to_dict())
        _validate_schema(spec.to_dict())
    except (TypeError, ValueError) as exc:
        return ValidationReport(False, [str(exc)])
    p = spec.population
    if not spec.name.strip() or not spec.domain.strip():
        errors.append("Challenge name and domain must be nonempty")
    for name in ("n", "biological_replicates", "sections_per_subject", "seed"):
        if type(getattr(p, name)) is not int:
            errors.append(f"{name} must be an integer")
    if p.seed < 0:
        errors.append("seed must be nonnegative")
    if any(type(count) is not int for count in p.groups.values()):
        errors.append("Group counts must be integers")
    if sum(p.groups.values()) != p.n:
        errors.append("Group counts must sum to n")
    if any(not group.strip() for group in p.groups):
        errors.append("Group names must be nonempty")
    names = [feature.name for feature in spec.features]
    if len(set(names)) != len(names):
        errors.append("Feature names must be unique")
    structure = [p.group_field, p.subject_field, p.section_field, p.observation_field]
    reserved = {"population_id", "biological_replicate", "synthetic"}
    if len(set(structure)) != 4 or any(not name.strip() or name in reserved for name in structure):
        errors.append("Hierarchy fields must be nonempty, distinct and not reserved")
    if set(names) & (reserved | set(structure)):
        errors.append("Feature names cannot overwrite identity or hierarchy fields")
    if len(set(p.copula_features)) != len(p.copula_features):
        errors.append("copula_features must be unique")
    latent_names = {
        f.name for f in spec.features if f.distribution in {"normal", "uniform", "lognormal"}
    }
    if set(p.copula_features) - latent_names:
        errors.append("Copula features must refer to normal, uniform or lognormal marginals")
    if p.correlation is None and p.copula_features:
        errors.append("copula_features requires a correlation matrix")
    if p.correlation is not None:
        try:
            corr = validate_correlation(p.correlation)
            if len(p.copula_features) != corr.shape[0]:
                errors.append("copula_features length must match correlation matrix dimension")
        except ValueError as exc:
            errors.append(str(exc))
    allowed = {
        "normal": {"mean", "sd"},
        "uniform": {"low", "high"},
        "lognormal": {"mean", "sigma"},
        "bernoulli": {"prob"},
        "categorical": {"categories", "probabilities"},
        "constant": {"value"},
    }
    for f in spec.features:
        prefix = f"{f.name}: "
        if not f.name.strip():
            errors.append("Feature names must be nonempty")
        if set(f.params) - allowed[f.distribution]:
            errors.append(prefix + "unknown distribution parameters")
        if f.min_value is not None and f.max_value is not None and f.min_value > f.max_value:
            errors.append(prefix + "min_value > max_value")
        if f.dtype == "integer" and f.min_value is not None and f.max_value is not None:
            if math.ceil(f.min_value) > math.floor(f.max_value):
                errors.append(prefix + "bounds contain no integer")
        if f.dtype == "categorical" and f.distribution not in {"categorical", "constant"}:
            errors.append(
                prefix + "categorical dtype requires categorical or constant distribution"
            )
        if f.distribution == "categorical" and f.dtype != "categorical":
            errors.append(prefix + "categorical distribution requires categorical dtype")
        if f.dtype == "binary" and f.distribution not in {"bernoulli", "constant"}:
            errors.append(prefix + "binary dtype requires Bernoulli or constant distribution")
        if f.distribution == "bernoulli" and f.dtype != "binary":
            errors.append(prefix + "Bernoulli distribution requires binary dtype")
        if f.dtype == "categorical" and (f.min_value is not None or f.max_value is not None):
            errors.append(prefix + "categorical bounds are unsupported")
        if f.distribution in {"normal", "lognormal", "uniform"}:
            if any(not _number(value) for value in f.params.values()):
                errors.append(prefix + "distribution parameters must be finite numbers")
                continue
            scale = (
                f.params.get("sd", 1.0)
                if f.distribution == "normal"
                else f.params.get("sigma", 1.0)
            )
            if f.distribution in {"normal", "lognormal"} and scale <= 0:
                errors.append(prefix + "SD/sigma must be positive")
            if f.distribution == "uniform" and f.params.get("high", 1.0) <= f.params.get(
                "low", 0.0
            ):
                errors.append(prefix + "uniform high must exceed low")
            if f.dtype != "integer" and f.min_value is not None and f.max_value is not None:
                if f.min_value == f.max_value:
                    errors.append(prefix + "continuous bounds have zero probability support")
            if f.distribution == "lognormal" and f.max_value is not None and f.max_value <= 0:
                errors.append(prefix + "lognormal upper bound must be positive")
        if f.distribution == "bernoulli":
            prob = f.params.get("prob", 0.5)
            if not _number(prob) or not 0 <= prob <= 1:
                errors.append(prefix + "Bernoulli probability must lie in [0,1]")
        if f.distribution == "categorical":
            categories = f.params.get("categories")
            if not isinstance(categories, list) or not categories:
                errors.append(prefix + "categorical requires nonempty categories")
            else:
                if any(isinstance(v, (dict, list)) for v in categories):
                    errors.append(prefix + "categories must be JSON scalars")
                if len({canonical_json(v) for v in categories}) != len(categories):
                    errors.append(prefix + "categories must be unique")
                probabilities = f.params.get("probabilities")
                if probabilities is not None and (
                    not isinstance(probabilities, list)
                    or len(probabilities) != len(categories)
                    or any(not _number(v) or v < 0 for v in probabilities)
                    or not math.isclose(sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-8)
                ):
                    errors.append(
                        prefix + "category probabilities must match labels and sum to one"
                    )
        if f.distribution == "constant":
            value = f.params.get("value")
            if value is None or isinstance(value, (dict, list)):
                errors.append(prefix + "constant requires a non-null scalar value")
            if f.dtype != "categorical" and not _number(value):
                errors.append(prefix + "numeric constant must be finite and numeric")
            elif f.dtype == "integer" and value is not None and int(value) != value:
                errors.append(prefix + "integer constant must be integral")
            elif f.dtype == "binary" and value not in (0, 1):
                errors.append(prefix + "binary constant must be zero or one")
        if (
            f.distribution == "constant"
            and f.dtype != "categorical"
            and _number(f.params.get("value"))
        ):
            for group in p.groups:
                effect = f.effects.get(group, {})
                result = f.params["value"] * effect.get("scale", 1.0) + effect.get("shift", 0.0)
                if not _number(result):
                    errors.append(prefix + "constant effect must produce a finite number")
                elif (f.min_value is not None and result < f.min_value) or (
                    f.max_value is not None and result > f.max_value
                ):
                    errors.append(prefix + "constant value violates feature bounds")
                elif f.dtype == "integer" and int(result) != result:
                    errors.append(prefix + "constant effect must produce an integer")
                elif f.dtype == "binary" and result not in (0, 1):
                    errors.append(prefix + "constant effect must produce a binary value")
        for group, effect in f.effects.items():
            if group not in p.groups:
                errors.append(prefix + f"effect references unknown group {group!r}")
            if (f.distribution in {"bernoulli", "categorical"} or f.dtype == "categorical") and (
                effect.get("shift", 0.0) != 0 or effect.get("scale", 1.0) != 1
            ):
                errors.append(prefix + "affine effects are unsupported for discrete distributions")
    if spec.constraints:
        from .constraints import declarative_constraint

        available = reserved | set(structure) | set(names)
        constraint_names = [c["name"] for c in spec.constraints]
        if len(set(constraint_names)) != len(constraint_names):
            errors.append("Constraint names must be unique")
        for constraint in spec.constraints:
            try:
                declarative_constraint(constraint, available)
            except ValueError as exc:
                errors.append(str(exc))
    if any(0 < count < p.biological_replicates for count in p.groups.values()):
        warnings.append("Actual subjects per group are capped by the observation count")
    return ValidationReport(
        not errors, errors, warnings, {"n_features": len(spec.features), "n_groups": len(p.groups)}
    )


def validate_population(rows: list[dict], spec: ChallengeSpec) -> ValidationReport:
    initial = validate_challenge(spec)
    if not initial.valid:
        return initial
    errors: list[str] = []
    warnings = list(initial.warnings)

    def error(message: str) -> None:
        if message not in errors:
            errors.append(message)

    try:
        canonical_json(rows)
    except (TypeError, ValueError) as exc:
        return ValidationReport(False, [str(exc)])
    if any(not isinstance(row, dict) for row in rows):
        return ValidationReport(False, errors + ["Population rows must be objects"])
    p = spec.population
    if len(rows) != p.n:
        error(f"Expected {p.n} rows, got {len(rows)}")
    for identity in ("population_id", p.observation_field):
        ids = [row.get(identity) for row in rows]
        if any(not isinstance(value, str) or not value.strip() for value in ids):
            error(f"Missing/nonempty identity required: {identity}")
        elif len(set(ids)) != len(ids):
            error(f"{identity} values must be unique")
    observed: dict[str, int] = {}
    subject_groups: dict[str, str] = {}
    section_subjects: dict[str, str] = {}
    subject_replicates: dict[str, int] = {}
    replicate_subjects: dict[tuple[str, int], str] = {}
    subject_counts: dict[str, int] = {}
    for row in rows:
        group = row.get(p.group_field)
        if not isinstance(group, str) or group not in p.groups:
            error("Unknown or missing group")
            continue
        observed[group] = observed.get(group, 0) + 1
        if row.get("synthetic") is not True:
            error("Every population row must include synthetic=true")
        subject, section = row.get(p.subject_field), row.get(p.section_field)
        if (
            not isinstance(subject, str)
            or not subject
            or not isinstance(section, str)
            or not section
        ):
            error("Missing subject or section identity")
            continue
        if subject_groups.setdefault(subject, group) != group:
            error("Subject is assigned to multiple groups")
        if section_subjects.setdefault(section, subject) != subject:
            error("Section is assigned to multiple subjects")
        subject_counts[subject] = subject_counts.get(subject, 0) + 1
        replicate = row.get("biological_replicate")
        if type(replicate) is not int or not 1 <= replicate <= p.biological_replicates:
            error("Biological replicate indices must be positive integers within the specification")
        else:
            if subject_replicates.setdefault(subject, replicate) != replicate:
                error("Subject has inconsistent biological replicate indices")
            if replicate_subjects.setdefault((group, replicate), subject) != subject:
                error("Biological replicate index identifies multiple subjects in one group")
    if observed != {group: count for group, count in p.groups.items() if count}:
        error("Group counts mismatch")
    for group, count in p.groups.items():
        actual = [sid for sid, g in subject_groups.items() if g == group]
        if len(actual) != min(p.biological_replicates, count):
            error("Actual subject counts do not match the specified hierarchy")
        sizes = [subject_counts[sid] for sid in actual]
        if sizes and max(sizes) - min(sizes) > 1:
            error("Observations are not balanced across subjects")
    from collections import Counter

    section_counts = Counter(section_subjects.values())
    for subject, count in subject_counts.items():
        if section_counts[subject] != min(p.sections_per_subject, count):
            error("Actual sections do not match the specified hierarchy")
    for f in spec.features:
        labels = (
            {canonical_json(v) for v in f.params["categories"]}
            if f.distribution == "categorical"
            else set()
        )
        for row in rows:
            if f.name not in row:
                error(f"Missing feature: {f.name}")
                continue
            value = row[f.name]
            if f.dtype != "categorical":
                if not _number(value):
                    error(f"{f.name}: expected a finite numeric value")
                    continue
                if f.dtype in {"integer", "binary"} and (type(value) is not int):
                    error(f"{f.name}: expected integer values")
                if f.dtype == "binary" and value not in (0, 1):
                    error(f"{f.name}: expected binary values")
                if (f.min_value is not None and value < f.min_value) or (
                    f.max_value is not None and value > f.max_value
                ):
                    error(f"{f.name}: feature bounds violated")
            elif f.distribution == "categorical":
                if canonical_json(value) not in labels:
                    error(f"{f.name}: unknown category")
    if spec.constraints:
        from .constraints import ConstraintEngine

        available = {
            "population_id",
            "biological_replicate",
            "synthetic",
            p.group_field,
            p.subject_field,
            p.section_field,
            p.observation_field,
        } | {f.name for f in spec.features}
        report = ConstraintEngine.from_specs(spec.constraints, available).validate(rows)
        if not report.valid:
            error("Population violates error constraints")
        if any(v["severity"] == "warning" for v in report.violations):
            warnings.append("Population violates warning constraints")
    return ValidationReport(not errors, errors, warnings, {"observed_groups": observed})
