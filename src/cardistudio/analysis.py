from __future__ import annotations

from collections import Counter
import math
from typing import Any


def summarize_population(rows: list[dict]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "features": {}}

    keys = [key for key in rows[0] if key != "population_id"]
    output: dict[str, Any] = {"n": len(rows), "features": {}}
    for key in keys:
        values = [row[key] for row in rows if row.get(key) is not None]
        if not values:
            continue
        if isinstance(values[0], (int, float)) and not isinstance(values[0], bool):
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / max(1, len(values) - 1)
            output["features"][key] = {
                "type": "numeric",
                "n": len(values),
                "mean": mean,
                "sd": math.sqrt(variance),
                "min": min(values),
                "max": max(values),
            }
        else:
            counts = Counter(map(str, values))
            output["features"][key] = {
                "type": "categorical",
                "n": len(values),
                "counts": dict(counts),
            }
    return output


def balance_report(
    rows: list[dict], group_field: str, features: list[str]
) -> dict[str, Any]:
    groups = sorted({str(row.get(group_field)) for row in rows})
    result: dict[str, Any] = {
        "group_field": group_field,
        "groups": {
            group: sum(str(row.get(group_field)) == group for row in rows)
            for group in groups
        },
        "features": {},
    }
    for feature in features:
        by_group = {
            group: [
                row[feature]
                for row in rows
                if str(row.get(group_field)) == group
                and isinstance(row.get(feature), (int, float))
            ]
            for group in groups
        }
        result["features"][feature] = {
            group: (sum(values) / len(values) if values else None)
            for group, values in by_group.items()
        }
    return result
