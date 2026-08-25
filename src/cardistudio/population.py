from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import json, hashlib
import numpy as np
from .models import ChallengeSpec, FeatureSpec

@dataclass
class Population:
    rows: list[dict]
    provenance: dict

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(x, sort_keys=True) for x in self.rows) + ("\n" if self.rows else "")

class PopulationBuilder:
    def __init__(self, spec: ChallengeSpec):
        self.spec = spec
        self.rng = np.random.default_rng(spec.population.seed)

    def _sample_feature(self, f: FeatureSpec, n: int):
        p = f.params
        d = f.distribution
        if d == "normal": x = self.rng.normal(p.get("mean", 0), p.get("sd", 1), n)
        elif d == "uniform": x = self.rng.uniform(p.get("low", 0), p.get("high", 1), n)
        elif d == "lognormal": x = self.rng.lognormal(p.get("mean", 0), p.get("sigma", 1), n)
        elif d == "bernoulli": x = self.rng.binomial(1, p.get("prob", .5), n)
        elif d == "categorical": x = self.rng.choice(p["categories"], size=n, p=p.get("probabilities"))
        elif d == "constant": x = np.repeat(p.get("value"), n)
        else: raise ValueError(f"Unsupported distribution: {d}")
        if f.min_value is not None: x = np.maximum(x, f.min_value)
        if f.max_value is not None: x = np.minimum(x, f.max_value)
        if f.dtype == "integer": x = np.rint(x).astype(int)
        if f.dtype == "binary": x = (np.asarray(x) > .5).astype(int)
        return x

    def build(self) -> Population:
        n = self.spec.population.n
        groups = self.spec.population.groups.copy()
        if sum(groups.values()) != n:
            raise ValueError("Population group counts must sum to n")
        conditions = np.concatenate([np.repeat(k, v) for k, v in groups.items()])
        self.rng.shuffle(conditions)
        rows = []
        feature_values = {f.name: self._sample_feature(f, n) for f in self.spec.features}
        for i in range(n):
            row = {"population_id": f"CS-{i+1:06d}", self.spec.population.group_field: str(conditions[i])}
            for f in self.spec.features: row[f.name] = feature_values[f.name][i].item() if hasattr(feature_values[f.name][i], "item") else feature_values[f.name][i]
            row["biological_replicate"] = (i % max(1, self.spec.population.biological_replicates)) + 1
            rows.append(row)
        prov = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": self.spec.population.seed,
            "challenge_fingerprint": self.spec.fingerprint(),
            "n": n,
            "generator": "Virelion-CardiStudio/0.1.0",
        }
        payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
        prov["population_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
        return Population(rows, prov)
