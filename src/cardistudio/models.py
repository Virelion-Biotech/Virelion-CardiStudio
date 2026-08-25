from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Literal
import hashlib, json

Distribution = Literal["normal", "uniform", "lognormal", "bernoulli", "categorical", "constant"]

@dataclass
class FeatureSpec:
    name: str
    dtype: Literal["continuous", "integer", "binary", "categorical"]
    distribution: Distribution = "normal"
    params: dict[str, Any] = field(default_factory=dict)
    unit: str | None = None
    description: str = ""
    min_value: float | None = None
    max_value: float | None = None

@dataclass
class PopulationSpec:
    n: int = 1000
    groups: dict[str, int] = field(default_factory=lambda: {"control": 500, "injury": 500})
    group_field: str = "condition"
    biological_replicates: int = 1
    seed: int = 42

@dataclass
class ChallengeSpec:
    name: str
    version: str = "1.0"
    domain: str = "cardiac"
    description: str = ""
    population: PopulationSpec = field(default_factory=PopulationSpec)
    features: list[FeatureSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    interventions: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChallengeSpec":
        pop = PopulationSpec(**data.get("population", {}))
        features = [FeatureSpec(**x) for x in data.get("features", [])]
        return cls(**{**data, "population": pop, "features": features})

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()
