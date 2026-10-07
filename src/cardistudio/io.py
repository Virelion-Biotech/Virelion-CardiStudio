from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .models import ChallengeSpec, migrate_challenge_dict
from .population import Population
from .serialization import canonical_json, population_digest, strict_loads

_PACKAGE_SCHEMA_PATH = Path(__file__).with_name("challenge_schema.json")


def _validate_schema(data: dict[str, Any]) -> None:
    schema = strict_loads(_PACKAGE_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda error: tuple(map(str, error.path)),
    )
    if errors:
        details = "; ".join(
            f"{list(error.path) or '<root>'}: {error.message}" for error in errors[:8]
        )
        raise ValueError(f"Challenge schema validation failed: {details}")


def _write(path: str | Path, text: str) -> None:
    """Replace each output atomically after serializing and validating its contents."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False, newline=""
        ) as handle:
            temporary = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def save_challenge(spec: ChallengeSpec, path: str | Path) -> None:
    from .validation import validate_challenge

    validate_challenge(spec).raise_if_invalid()
    _write(path, json.dumps(spec.to_dict(), indent=2, sort_keys=True, allow_nan=False))


def loads_challenge(text: str | bytes) -> ChallengeSpec:
    raw = strict_loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Challenge document must be a JSON object")
    _validate_schema(raw)
    migrated = migrate_challenge_dict(raw)
    _validate_schema(migrated)
    spec = ChallengeSpec.from_dict(migrated)
    from .validation import validate_challenge

    validate_challenge(spec).raise_if_invalid()
    return spec


def load_challenge(path: str | Path) -> ChallengeSpec:
    return loads_challenge(Path(path).read_text(encoding="utf-8"))


def _check_population(pop: Population) -> str:
    if pop.provenance.get("synthetic") is not True:
        raise ValueError("Synthetic-data attestation missing from population provenance")
    _check_rows(pop.rows)
    canonical_json(pop.provenance)
    digest = population_digest(pop.rows)
    recorded = pop.provenance.get("population_sha256")
    if recorded is not None and recorded != digest:
        raise ValueError("Population contents do not match recorded fingerprint")
    return digest


def _check_rows(rows: list[dict[str, Any]]) -> None:
    if any(not isinstance(row, dict) or row.get("synthetic") is not True for row in rows):
        raise ValueError("Every population row must be an object with synthetic=true")
    canonical_json(rows)


def save_population(pop: Population, path: str | Path) -> None:
    digest = _check_population(pop)
    provenance = dict(pop.provenance, population_sha256=digest)
    rows = pop.to_jsonl()
    metadata = json.dumps(provenance, indent=2, sort_keys=True, allow_nan=False)
    path = Path(path)
    # Two-file publication cannot be one filesystem transaction; readers verify both.
    _write(path.with_suffix(path.suffix + ".provenance.json"), metadata)
    _write(path, rows)


def load_population(path: str | Path, *, verify_provenance: bool = True) -> list[dict[str, Any]]:
    path = Path(path)
    rows = [
        strict_loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    _check_rows(rows)
    if verify_provenance:
        sidecar = path.with_suffix(path.suffix + ".provenance.json")
        if not sidecar.exists():
            raise ValueError("Population provenance sidecar is required for verified loading")
        provenance = strict_loads(sidecar.read_text(encoding="utf-8"))
        if (
            not isinstance(provenance, dict)
            or provenance.get("synthetic") is not True
            or provenance.get("population_sha256") != population_digest(rows)
        ):
            raise ValueError("Population provenance/fingerprint verification failed")
        if provenance.get("n", len(rows)) != len(rows):
            raise ValueError("Population size does not match provenance")
    return rows


def population_csv(rows: list[dict[str, Any]]) -> str:
    _check_rows(rows)
    if not rows:
        return ""
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def save_csv(rows: list[dict], path: str | Path) -> None:
    _write(path, population_csv(rows))


def _check_export(spec: ChallengeSpec, pop: Population) -> None:
    from .validation import validate_population

    _check_population(pop)
    validate_population(pop.rows, spec).raise_if_invalid()
    if pop.provenance.get("challenge_fingerprint") != spec.fingerprint():
        raise ValueError("Population was not generated from the supplied challenge")


def export_cardi_bridge(spec: ChallengeSpec, pop: Population, path: str | Path) -> None:
    """Export the legacy CardiStudio study bundle; not a CardiBridge wire envelope."""
    _check_export(spec, pop)
    payload = {
        "schema": "virelion.cardistudio.challenge.v1",
        "synthetic": True,
        "challenge": spec.to_dict(),
        "provenance": pop.provenance,
        "population": pop.rows,
    }
    _write(path, json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))


def cardi_bridge_envelope(
    spec: ChallengeSpec, pop: Population, consumer: str = "CardiVex"
) -> dict[str, Any]:
    """Build a canonical agent.challenge envelope without requiring CardiBridge."""
    _check_export(spec, pop)
    if not isinstance(consumer, str) or not consumer.strip():
        raise ValueError("Consumer must be nonempty")
    identity = spec.fingerprint() + ":" + population_digest(pop.rows) + ":" + consumer
    import hashlib

    message_id = hashlib.sha256(identity.encode()).hexdigest()
    timestamp = pop.provenance["created_at"]
    trace = {
        "trace_id": message_id[:32],
        "span_id": message_id[:16],
        "source": "CardiStudio",
        "schema_version": "1.0.0",
        "created_at": timestamp,
        "provenance": {
            "synthetic": True,
            "challenge": spec.to_dict(),
            "generation": pop.provenance,
        },
    }
    return {
        "message_id": message_id,
        "message_type": "agent.challenge",
        "producer": "CardiStudio",
        "consumer": consumer,
        "idempotency_key": "cardistudio:" + message_id,
        "timestamp": timestamp,
        "trace": trace,
        "payload": {
            "challenge_id": spec.fingerprint(),
            "challenge_type": spec.name,
            "population": pop.rows,
            "intended_task": spec.description or "Synthetic benchmark",
            "trace": trace,
        },
    }


def export_cardi_bridge_envelope(
    spec: ChallengeSpec, pop: Population, path: str | Path, consumer: str = "CardiVex"
) -> None:
    _write(
        path,
        json.dumps(
            cardi_bridge_envelope(spec, pop, consumer), indent=2, sort_keys=True, allow_nan=False
        ),
    )
