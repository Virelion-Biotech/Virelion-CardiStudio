from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class Constraint:
    name: str
    predicate: Callable[[dict[str, Any]], bool]
    severity: str = "error"

@dataclass
class ConstraintReport:
    valid: bool
    violations: list[dict[str, Any]]

class ConstraintEngine:
    def __init__(self, constraints: list[Constraint] | None = None):
        self.constraints = constraints or []

    def validate(self, rows: list[dict[str, Any]]) -> ConstraintReport:
        violations = []
        for i, row in enumerate(rows):
            for c in self.constraints:
                try:
                    ok = bool(c.predicate(row))
                except Exception as exc:
                    ok = False
                    violations.append({"row": i, "constraint": c.name, "severity": "error", "error": str(exc)})
                    continue
                if not ok:
                    violations.append({"row": i, "constraint": c.name, "severity": c.severity})
        return ConstraintReport(not any(v["severity"] == "error" for v in violations), violations)


def range_constraint(name: str, field: str, minimum: float | None = None, maximum: float | None = None) -> Constraint:
    def predicate(row):
        value = row[field]
        return (minimum is None or value >= minimum) and (maximum is None or value <= maximum)
    return Constraint(name, predicate)


def relationship_constraint(name: str, expression: Callable[[dict[str, Any]], bool]) -> Constraint:
    return Constraint(name, expression)
