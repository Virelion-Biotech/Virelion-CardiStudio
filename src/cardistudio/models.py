from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal
import hashlib
import json

Distribution = Literal["normal", "uniform", "lognormal", "bernoulli", "categorical", "constant"]
CURRENT_CHALLENGE_VERSION = "1.1"


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
    # Group-conditional changes to the marginal parameters.
    # Example: {"mi": {"shift": -0.22, "scale": 1.4}}
    effects: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class PopulationSpec:
    n: int = 1000
    groups: dict[str, int] = field(default_factory=lambda: {"control": 500, "injury": 500})
    group_field: str = "condition"
    biological_replicates: int = 1
    sections_per_subject: int = 1
    intraclass_correlation: float = 0.0
    subject_field: str = "subject_id"
    section_field: str = "section_id"
    observation_field: str = "observation_id"
    copula_features: list[str] = field(default_factory=list)
    correlation: list[list[float]] | None = None
    seed: int = 42


@dataclass
class ChallengeSpec:
    name: str
    version: str = CURRENT_CHALLENGE_VERSION
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


def migrate_challenge_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate supported 1.x challenge documents to the current model."""
    version = str(data.get("version", "1.0"))
    major = version.split(".", 1)[0]
    current_major = CURRENT_CHALLENGE_VERSION.split(".", 1)[0]
    if major != current_major:
        raise ValueError(
            f"Unsupported challenge major version {version}; expected {current_major}.x"
        )

    migrated = json.loads(json.dumps(data))
    for feature in migrated.get("features", []):
        feature.setdefault("effects", {})
    pop = migrated.setdefault("population", {})
    pop.setdefault("sections_per_subject", 1)
    pop.setdefault("intraclass_correlation", 0.0)
    pop.setdefault("subject_field", "subject_id")
    pop.setdefault("section_field", "section_id")
    pop.setdefault("observation_field", "observation_id")
    pop.setdefault("copula_features", [])
    pop.setdefault("correlation", None)
    migrated["version"] = CURRENT_CHALLENGE_VERSION
    return migrated
