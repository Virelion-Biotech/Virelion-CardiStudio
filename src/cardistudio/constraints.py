from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Constraint:
    name: str
    predicate: Callable[[dict[str, Any]], bool]
    severity: str = "error"
    expression: str | None = None


@dataclass
class ConstraintReport:
    valid: bool
    violations: list[dict[str, Any]]


_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.Name, ast.Load,
    ast.Constant, ast.UnaryOp, ast.Not, ast.UAdd, ast.USub, ast.BinOp, ast.Add,
    ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Eq, ast.NotEq,
)


def _split_top_level_implies(expression: str) -> tuple[str, str] | None:
    depth = 0
    in_quote: str | None = None
    i = 0
    while i <= len(expression) - 9:
        ch = expression[i]
        if ch in {"\" ", "'"}:
            if in_quote == ch:
                in_quote = None
            elif in_quote is None:
                in_quote = ch
        elif in_quote is None:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif depth == 0 and expression[i : i + 9] == " implies ":
                return expression[:i].strip(), expression[i + 9 :].strip()
        i += 1
    return None


def _parse(expression: str) -> ast.Expression:
    implication = _split_top_level_implies(expression)
    if implication:
        lhs, rhs = implication
        expression = f"(not ({lhs})) or ({rhs})"
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"Unsupported expression element: {type(node).__name__}")
    return tree


def expression_names(expression: str) -> set[str]:
    tree = _parse(expression)
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _evaluate(node: ast.AST, row: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, row)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in row:
            raise KeyError(node.id)
        return row[node.id]
    if isinstance(node, ast.BoolOp):
        values = [_evaluate(value, row) for value in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.UnaryOp):
        value = _evaluate(node.operand, row)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.UAdd):
            return +value
        return -value
    if isinstance(node, ast.BinOp):
        left, right = _evaluate(node.left, row), _evaluate(node.right, row)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        if isinstance(node.op, ast.Mod):
            return left % right
    if isinstance(node, ast.Compare):
        left = _evaluate(node.left, row)
        for op, comparator in zip(node.ops, node.comparators):
            right = _evaluate(comparator, row)
            if isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            else:
                raise ValueError(f"Unsupported comparator {type(op).__name__}")
            if not ok:
                return False
            left = right
        return True
    raise ValueError(f"Unsupported AST node {type(node).__name__}")


def declarative_constraint(
    spec: dict[str, Any], available_fields: set[str] | None = None
) -> Constraint:
    if spec.get("type") != "relation":
        raise ValueError(f"Unsupported declarative constraint type: {spec.get('type')}")
    name = str(spec.get("name", "")).strip()
    expression = str(spec.get("expr", "")).strip()
    severity = str(spec.get("severity", "error"))
    if not name or not expression:
        raise ValueError("Declarative constraints require name and expr")
    if severity not in {"error", "warning"}:
        raise ValueError("Constraint severity must be 'error' or 'warning'")
    names = expression_names(expression)
    if available_fields is not None:
        unknown = names - available_fields
        if unknown:
            raise ValueError(
                f"Constraint {name!r} references unknown fields: {sorted(unknown)}"
            )
    tree = _parse(expression)
    return Constraint(
        name,
        lambda row, t=tree: bool(_evaluate(t, row)),
        severity,
        expression,
    )


class ConstraintEngine:
    def __init__(self, constraints: list[Constraint] | None = None):
        self.constraints = constraints or []

    @classmethod
    def from_specs(
        cls, specs: list[dict[str, Any]], available_fields: set[str]
    ) -> "ConstraintEngine":
        return cls([declarative_constraint(spec, available_fields) for spec in specs])

    def validate(self, rows: list[dict[str, Any]]) -> ConstraintReport:
        violations = []
        for index, row in enumerate(rows):
            for constraint in self.constraints:
                try:
                    ok = bool(constraint.predicate(row))
                except Exception as exc:
                    violations.append(
                        {
                            "row": index,
                            "constraint": constraint.name,
                            "severity": "error",
                            "error": str(exc),
                        }
                    )
                    continue
                if not ok:
                    violations.append(
                        {
                            "row": index,
                            "constraint": constraint.name,
                            "severity": constraint.severity,
                        }
                    )
        return ConstraintReport(
            not any(v["severity"] == "error" for v in violations), violations
        )


def range_constraint(
    name: str,
    field: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> Constraint:
    def predicate(row: dict[str, Any]) -> bool:
        value = row[field]
        return (minimum is None or value >= minimum) and (
            maximum is None or value <= maximum
        )

    return Constraint(name, predicate)


def relationship_constraint(
    name: str, expression: Callable[[dict[str, Any]], bool]
) -> Constraint:
    return Constraint(name, expression)
