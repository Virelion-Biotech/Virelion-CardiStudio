"""Strict JSON boundaries for portable specifications and population identities."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _check(value: Any) -> None:
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        for child in value.values():
            _check(child)
    elif isinstance(value, list):
        for child in value:
            _check(child)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
    elif value is not None and not isinstance(value, (str, bool, int)):
        raise ValueError(f"Unsupported JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    _check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def population_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json(rows).encode("utf-8")).hexdigest()


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str) -> Any:
    raise ValueError(f"Non-finite JSON constant: {value}")


def strict_loads(text: str | bytes) -> Any:
    result = json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    _check(result)
    return result
