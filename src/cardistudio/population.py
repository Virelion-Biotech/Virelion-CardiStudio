from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import hashlib
import json
import math
from typing import Any

import numpy as np
from scipy.stats import norm, truncnorm

from .constraints import ConstraintEngine
from .correlations import gaussian_copula, validate_correlation
from .models import ChallengeSpec, FeatureSpec

try:
    GENERATOR_VERSION = version("virelion-cardistudio")
except PackageNotFoundError:
    GENERATOR_VERSION = "0+local"


@dataclass
class Population:
    rows: list[dict[str, Any]]
    provenance: dict[str, Any]

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(row, sort_keys=True, default=str) for row in self.rows) + (
            "\n" if self.rows else ""
        )


class PopulationBuilder:
    """Generate group-conditional, correlated, hierarchically nested populations."""

    _LATENT_DISTRIBUTIONS = {"normal", "uniform", "lognormal"}

    def __init__(self, spec: ChallengeSpec):
        self.spec = spec
        self.rng = np.random.default_rng(spec.population.seed)
        self.latent_features = [f for f in spec.features if f.distribution in self._LATENT_DISTRIBUTIONS]
        self._feature_index = {f.name: i for i, f in enumerate(self.latent_features)}
        p = spec.population
        available = {
            "population_id", p.group_field, p.subject_field, p.section_field,
            p.observation_field, "biological_replicate", "synthetic",
        } | {f.name for f in spec.features}
        self.constraint_engine = ConstraintEngine.from_specs(spec.constraints, available)
        self._correlation = self._build_correlation()

    def _build_correlation(self) -> np.ndarray:
        d = len(self.latent_features)
        if not d:
            return np.empty((0, 0), dtype=float)
        corr = np.eye(d, dtype=float)
        configured = self.spec.population.correlation
        names = self.spec.population.copula_features
        if configured is None:
            return corr
        target = validate_correlation(configured)
        if len(names) != target.shape[0]:
            raise ValueError("copula_features length must match correlation matrix dimension")
        if len(set(names)) != len(names):
            raise ValueError("copula_features must be unique")
        unknown = [name for name in names if name not in self._feature_index]
        if unknown:
            raise ValueError(f"Copula features must be continuous: {unknown}")
        for i, name_i in enumerate(names):
            for j, name_j in enumerate(names):
                corr[self._feature_index[name_i], self._feature_index[name_j]] = target[i, j]
        validate_correlation(corr.tolist())
        return corr

    @staticmethod
    def _effect(feature: FeatureSpec, group: str) -> tuple[float, float]:
        effect = feature.effects.get(group, {})
        shift = float(effect.get("shift", 0.0))
        scale = float(effect.get("scale", 1.0))
        if scale <= 0:
            raise ValueError(f"{feature.name}: effect scale must be > 0 for group {group!r}")
        if feature.distribution in {"bernoulli", "categorical"} and (shift or scale != 1.0):
            raise ValueError(f"{feature.name}: affine effects are unsupported for {feature.distribution}")
        return shift, scale

    @staticmethod
    def _truncation_mass(mean: float, sd: float, low: float | None, high: float | None) -> float:
        if low is None and high is None:
            return 0.0
        a = -np.inf if low is None else (low - mean) / sd
        b = np.inf if high is None else (high - mean) / sd
        kept = float(norm.cdf(b) - norm.cdf(a))
        return float(np.clip(1.0 - kept, 0.0, 1.0))

    def _sample_continuous(
        self, feature: FeatureSpec, z: np.ndarray, group: str
    ) -> tuple[np.ndarray, float]:
        p = feature.params
        shift, scale = self._effect(feature, group)
        d = feature.distribution

        if d == "normal":
            mean = float(p.get("mean", 0.0)) + shift
            sd = float(p.get("sd", 1.0)) * scale
            if sd <= 0:
                raise ValueError(f"{feature.name}: resulting SD must be > 0")
            if feature.min_value is None and feature.max_value is None:
                return mean + sd * z, 0.0
            a = -np.inf if feature.min_value is None else (feature.min_value - mean) / sd
            b = np.inf if feature.max_value is None else (feature.max_value - mean) / sd
            if a >= b:
                raise ValueError(f"{feature.name}: bounds leave no probability support")
            cdf_a, cdf_b = norm.cdf(a), norm.cdf(b)
            q = cdf_a + norm.cdf(z) * (cdf_b - cdf_a)
            return truncnorm.ppf(q, a, b, loc=mean, scale=sd), self._truncation_mass(
                mean, sd, feature.min_value, feature.max_value
            )

        if d == "uniform":
            low = float(p.get("low", 0.0)) * scale + shift
            high = float(p.get("high", 1.0)) * scale + shift
            if high <= low:
                raise ValueError(f"{feature.name}: resulting uniform high must exceed low")
            bounded_low = low if feature.min_value is None else max(low, feature.min_value)
            bounded_high = high if feature.max_value is None else min(high, feature.max_value)
            if bounded_low >= bounded_high:
                raise ValueError(f"{feature.name}: bounds leave no uniform support")
            u = norm.cdf(z)
            x = bounded_low + (bounded_high - bounded_low) * u
            return x, float(1.0 - (bounded_high - bounded_low) / (high - low))

        if d == "lognormal":
            log_mean = float(p.get("mean", 0.0)) + shift
            sigma = float(p.get("sigma", 1.0)) * scale
            if sigma <= 0:
                raise ValueError(f"{feature.name}: resulting sigma must be > 0")
            low_log = None if feature.min_value is None else math.log(feature.min_value)
            high_log = None if feature.max_value is None else math.log(feature.max_value)
            a = -np.inf if low_log is None else (low_log - log_mean) / sigma
            b = np.inf if high_log is None else (high_log - log_mean) / sigma
            if a >= b:
                raise ValueError(f"{feature.name}: lognormal bounds leave no support")
            cdf_a, cdf_b = norm.cdf(a), norm.cdf(b)
            q = cdf_a + norm.cdf(z) * (cdf_b - cdf_a)
            log_x = truncnorm.ppf(q, a, b, loc=log_mean, scale=sigma)
            return np.exp(log_x), self._truncation_mass(
                log_mean, sigma, low_log, high_log
            )

        raise ValueError(f"Unsupported continuous distribution: {d}")

    def _sample_feature(
        self, feature: FeatureSpec, z: np.ndarray | None, group: str, n: int, rng: np.random.Generator
    ) -> tuple[np.ndarray, float]:
        d = feature.distribution
        if d in self._LATENT_DISTRIBUTIONS:
            assert z is not None
            x, truncation = self._sample_continuous(feature, z, group)
        elif d == "bernoulli":
            prob = float(feature.params.get("prob", 0.5))
            if not 0 <= prob <= 1:
                raise ValueError(f"{feature.name}: bernoulli probability must be in [0, 1]")
            x = rng.binomial(1, prob, n)
            truncation = 0.0
        elif d == "categorical":
            x = rng.choice(
                feature.params["categories"], size=n, p=feature.params.get("probabilities")
            )
            truncation = 0.0
        elif d == "constant":
            x = np.repeat(feature.params.get("value"), n)
            shift, scale = self._effect(feature, group)
            if shift or scale != 1.0:
                x = np.asarray(x, dtype=float) * scale + shift
            truncation = 0.0
        else:
            raise ValueError(f"Unsupported distribution: {d}")

        if feature.dtype == "integer":
            x = np.rint(np.asarray(x, dtype=float)).astype(int)
        elif feature.dtype == "binary":
            x = (np.asarray(x) > 0.5).astype(int)
        return x, truncation

    def _make_structure(self) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
        p = self.spec.population
        rows: list[dict[str, Any]] = []
        by_group: dict[str, list[int]] = {}
        subject_number = 0

        for group, count in p.groups.items():
            reps = min(p.biological_replicates, count)
            subject_ids = [
                f"SUB-{subject_number + i + 1:04d}" for i in range(reps)
            ]
            subject_number += reps
            sizes = np.full(reps, count // reps, dtype=int)
            sizes[: count % reps] += 1
            assignments = np.concatenate(
                [np.repeat(subject_ids[i], sizes[i]) for i in range(reps)]
            )
            self.rng.shuffle(assignments)

            indices: list[int] = []
            section_counts = {sid: 0 for sid in subject_ids}
            replicate_map = {sid: i + 1 for i, sid in enumerate(subject_ids)}
            for sid in assignments.tolist():
                section_counts[sid] += 1
                section = ((section_counts[sid] - 1) % p.sections_per_subject) + 1
                row = {
                    "population_id": None,
                    p.group_field: str(group),
                    p.subject_field: sid,
                    p.section_field: f"{sid}-SEC-{section:02d}",
                    p.observation_field: None,
                    "biological_replicate": replicate_map[sid],
                    "synthetic": True,
                }
                rows.append(row)
                indices.append(len(rows) - 1)
            by_group[str(group)] = indices

        self.rng.shuffle(rows)
        remapped: dict[str, list[int]] = {group: [] for group in by_group}
        for i, row in enumerate(rows, start=1):
            row["population_id"] = f"CS-{i:06d}"
            row[self.spec.population.observation_field] = f"OBS-{i:06d}"
        for i, row in enumerate(rows):
            remapped[str(row[p.group_field])].append(i)
        return rows, remapped

    def _sample_group(
        self, rows: list[dict[str, Any]], group: str, seed: int
    ) -> tuple[dict[str, np.ndarray], dict[str, float], dict[str, Any]]:
        n = len(rows)
        d = len(self.latent_features)
        p = self.spec.population
        rng = np.random.default_rng(seed)
        subject_ids = [row[p.subject_field] for row in rows]
        unique_subjects = list(dict.fromkeys(subject_ids))
        subject_index = {sid: i for i, sid in enumerate(unique_subjects)}
        row_subject_index = np.asarray([subject_index[sid] for sid in subject_ids], dtype=int)

        if d:
            subject_latent = gaussian_copula(len(unique_subjects), self._correlation.tolist(), seed + 1)
            residual_latent = gaussian_copula(n, self._correlation.tolist(), seed + 2)
        else:
            subject_latent = np.empty((len(unique_subjects), 0))
            residual_latent = np.empty((n, 0))

        rho = p.intraclass_correlation
        values: dict[str, np.ndarray] = {}
        truncations: dict[str, float] = {}
        for feature in self.spec.features:
            if feature.name in self._feature_index:
                j = self._feature_index[feature.name]
                z = (
                    math.sqrt(rho) * subject_latent[row_subject_index, j]
                    + math.sqrt(1.0 - rho) * residual_latent[:, j]
                )
            else:
                z = None
            x, truncation = self._sample_feature(feature, z, group, n, rng)
            values[feature.name] = x
            truncations[feature.name] = truncation
        return values, truncations, {
            "subject_latent": subject_latent,
            "residual_latent": residual_latent,
            "row_subject_index": row_subject_index,
            "rng": rng,
        }

    @staticmethod
    def _apply(rows: list[dict[str, Any]], indices: list[int], values: dict[str, np.ndarray]) -> None:
        for name, array in values.items():
            for local_i, global_i in enumerate(indices):
                value = array[local_i]
                rows[global_i][name] = value.item() if hasattr(value, "item") else value

    def _ground_truth(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        group_names = list(self.spec.population.groups)
        truth: dict[str, Any] = {
            "group_counts": dict(self.spec.population.groups),
            "feature_effects": {
                f.name: {
                    group: {
                        "shift": float(effect.get("shift", 0.0)),
                        "scale": float(effect.get("scale", 1.0)),
                    }
                    for group, effect in f.effects.items()
                }
                for f in self.spec.features
            },
            "copula": {
                "features": list(self.spec.population.copula_features),
                "target_correlation": self.spec.population.correlation,
            },
            "hierarchy": {
                "biological_replicates": self.spec.population.biological_replicates,
                "sections_per_subject": self.spec.population.sections_per_subject,
                "intraclass_correlation": self.spec.population.intraclass_correlation,
            },
            "comparisons": {},
        }
        if len(group_names) < 2:
            return truth

        ref = group_names[0]
        for other in group_names[1:]:
            comparison: dict[str, Any] = {}
            for feature in self.spec.features:
                ref_values = [
                    row[feature.name]
                    for row in rows
                    if row[self.spec.population.group_field] == ref
                ]
                other_values = [
                    row[feature.name]
                    for row in rows
                    if row[self.spec.population.group_field] == other
                ]
                if feature.distribution in self._LATENT_DISTRIBUTIONS:
                    a = np.asarray(ref_values, dtype=float)
                    b = np.asarray(other_values, dtype=float)
                    entry: dict[str, Any] = {
                        "sample_mean_ref": float(np.mean(a)),
                        "sample_mean_other": float(np.mean(b)),
                    }
                    pooled = math.sqrt(
                        (float(np.var(a, ddof=1)) + float(np.var(b, ddof=1))) / 2
                    )
                    entry["sample_cohens_d"] = (
                        (float(np.mean(b)) - float(np.mean(a))) / pooled if pooled else None
                    )
                else:
                    entry = {
                        "sample_counts_ref": dict(
                            zip(*np.unique(np.asarray(ref_values, dtype=str), return_counts=True))
                        ),
                        "sample_counts_other": dict(
                            zip(*np.unique(np.asarray(other_values, dtype=str), return_counts=True))
                        ),
                    }
                    entry["sample_cohens_d"] = None
                if feature.distribution == "normal":
                    ref_shift, ref_scale = self._effect(feature, ref)
                    other_shift, other_scale = self._effect(feature, other)
                    ref_sd = float(feature.params.get("sd", 1.0)) * ref_scale
                    other_sd = float(feature.params.get("sd", 1.0)) * other_scale
                    ref_mean = float(feature.params.get("mean", 0.0)) + ref_shift
                    other_mean = float(feature.params.get("mean", 0.0)) + other_shift
                    entry["parameter_mean_ref"] = ref_mean
                    entry["parameter_mean_other"] = other_mean
                    entry["parameter_cohens_d"] = (other_mean - ref_mean) / math.sqrt(
                        (ref_sd**2 + other_sd**2) / 2
                    )
                comparison[feature.name] = entry
            truth["comparisons"][f"{other}_vs_{ref}"] = comparison
        return truth

    def build(self) -> Population:
        p = self.spec.population
        if sum(p.groups.values()) != p.n:
            raise ValueError("Population group counts must sum to n")
        if p.biological_replicates < 1 or p.sections_per_subject < 1:
            raise ValueError("biological_replicates and sections_per_subject must be >= 1")
        if not 0 <= p.intraclass_correlation < 1:
            raise ValueError("intraclass_correlation must be in [0, 1)")

        rows, by_group = self._make_structure()
        truncation_rates: dict[str, dict[str, float]] = {}
        group_states: dict[str, dict[str, Any]] = {}
        for offset, (group, indices) in enumerate(by_group.items()):
            group_rows = [rows[i] for i in indices]
            values, rates, state = self._sample_group(
                group_rows, group, p.seed + 1009 * (offset + 1)
            )
            self._apply(rows, indices, values)
            group_states[group] = {"indices": indices, "state": state}
            for feature, rate in rates.items():
                truncation_rates.setdefault(feature, {})[group] = rate

        constraint_rejected = 0
        constraint_candidates = 0
        if self.constraint_engine.constraints:
            inverse = {
                global_i: (group, local_i)
                for group, info in group_states.items()
                for local_i, global_i in enumerate(info["indices"])
            }
            for _ in range(100):
                report = self.constraint_engine.validate(rows)
                error_rows = sorted({
                    v["row"] for v in report.violations if v["severity"] == "error"
                })
                if not error_rows:
                    break
                constraint_rejected += len(error_rows)
                for global_i in error_rows:
                    group, local_i = inverse[global_i]
                    info = group_states[group]
                    state = info["state"]
                    residual = gaussian_copula(
                        1, self._correlation.tolist(), seed=int(
                            state["rng"].integers(0, 2**32 - 1)
                        )
                    )[0] if self.latent_features else np.empty(0)
                    rho = p.intraclass_correlation
                    row_z = (
                        math.sqrt(rho) * state["subject_latent"][state["row_subject_index"][local_i]]
                        + math.sqrt(1.0 - rho) * residual
                    ) if self.latent_features else np.empty(0)
                    one_row = [rows[global_i]]
                    for feature in self.spec.features:
                        z = None
                        if feature.name in self._feature_index:
                            z = np.asarray([row_z[self._feature_index[feature.name]]])
                        x, _ = self._sample_feature(
                            feature, z, group, 1, state["rng"]
                        )
                        value = x[0]
                        one_row[0][feature.name] = (
                            value.item() if hasattr(value, "item") else value
                        )
                    constraint_candidates += 1
            else:
                raise ValueError("Could not satisfy declarative constraints during generation")

        final_report = self.constraint_engine.validate(rows)
        if not final_report.valid:
            raise ValueError("Generated population violates one or more error constraints")

        ground_truth = self._ground_truth(rows)
        payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str).encode()
        provenance = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": p.seed,
            "challenge_fingerprint": self.spec.fingerprint(),
            "n": p.n,
            "generator": f"Virelion-CardiStudio/{GENERATOR_VERSION}",
            "synthetic": True,
            "hierarchy": ground_truth["hierarchy"],
            "generation": {
                "truncation_rejection_rates": truncation_rates,
                "constraint_enforcement": "generative_resampling"
                    if self.constraint_engine.constraints else "not_configured",
                "constraint_rejected_rows": constraint_rejected,
                "constraint_candidate_draws": constraint_candidates,
                "constraint_rejection_rate": (
                    constraint_rejected / constraint_candidates
                    if constraint_candidates else 0.0
                ),
            },
            "ground_truth": ground_truth,
            "population_sha256": hashlib.sha256(payload).hexdigest(),
        }
        return Population(rows, provenance)
