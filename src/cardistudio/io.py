from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .models import ChallengeSpec, migrate_challenge_dict
from .population import Population

_SOURCE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "cardistudio.challenge.v1.json"
)
_PACKAGE_SCHEMA_PATH = Path(__file__).with_name("challenge_schema.json")


def _validate_schema(data: dict[str, Any]) -> None:
    schema_path = _SOURCE_SCHEMA_PATH if _SOURCE_SCHEMA_PATH.exists() else _PACKAGE_SCHEMA_PATH
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(
            f"{list(error.path) or '<root>'}: {error.message}" for error in errors[:8]
        )
        raise ValueError(f"Challenge schema validation failed: {details}")


def save_challenge(spec: ChallengeSpec, path: str | Path) -> None:
    from .validation import validate_challenge

    validate_challenge(spec).raise_if_invalid()
    payload = spec.to_dict()
    _validate_schema(payload)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_challenge(path: str | Path) -> ChallengeSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Challenge document must be a JSON object")
    _validate_schema(raw)
    migrated = migrate_challenge_dict(raw)
    _validate_schema(migrated)
    spec = ChallengeSpec.from_dict(migrated)
    from .validation import validate_challenge

    validate_challenge(spec).raise_if_invalid()
    return spec


def save_population(pop: Population, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if pop.provenance.get("synthetic") is not True:
        raise ValueError("Synthetic-data attestation missing from population provenance")
    path.write_text(pop.to_jsonl(), encoding="utf-8")
    path.with_suffix(path.suffix + ".provenance.json").write_text(
        json.dumps(pop.provenance, indent=2, sort_keys=True), encoding="utf-8"
    )


def load_population(path: str | Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(row.get("synthetic") is not True for row in rows):
        raise ValueError("Population file is missing mandatory synthetic=true markers")
    return rows


def save_csv(rows: list[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    if any(row.get("synthetic") is not True for row in rows):
        raise ValueError("CSV export requires synthetic=true on every row")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_cardi_bridge(spec: ChallengeSpec, pop: Population, path: str | Path) -> None:
    if pop.provenance.get("synthetic") is not True:
        raise ValueError("CardiBridge export requires synthetic=true provenance")
    payload = {
        "schema": "virelion.cardistudio.challenge.v1",
        "synthetic": True,
        "challenge": spec.to_dict(),
        "provenance": pop.provenance,
        "population": pop.rows,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
