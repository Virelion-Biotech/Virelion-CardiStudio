from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any
import hashlib
import json


@dataclass(frozen=True)
class DesignCell:
    """One randomized experimental-design cell."""
    cell_id: str
    factors: dict[str, Any]
    replicate: int
    block: int
    randomization_order: int


def factorial_design(
    factors: dict[str, list[Any]],
    replicates: int = 1,
    blocks: int = 1,
    seed: int = 42,
) -> list[DesignCell]:
    """Build a deterministic, balanced full-factorial randomized design.

    Every factor combination receives exactly ``replicates`` observations.
    Blocks are assigned round-robin and the final order is deterministically
    shuffled from the supplied seed without changing the factor balance.
    """
    if not factors or any(not levels for levels in factors.values()):
        raise ValueError("factors must contain at least one non-empty level list")
    if replicates < 1 or blocks < 1:
        raise ValueError("replicates and blocks must be positive")

    import random
    names = list(factors)
    rows = []
    for combo in product(*(factors[name] for name in names)):
        values = dict(zip(names, combo))
        for replicate in range(1, replicates + 1):
            rows.append((values, replicate))

    rng = random.Random(seed)
    rng.shuffle(rows)
    cells: list[DesignCell] = []
    for order, (values, replicate) in enumerate(rows, start=1):
        canonical = json.dumps(
            {"factors": values, "replicate": replicate, "seed": seed},
            sort_keys=True,
            default=str,
        )
        cell_id = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        cells.append(
            DesignCell(
                cell_id=cell_id,
                factors=values,
                replicate=replicate,
                block=((order - 1) % blocks) + 1,
                randomization_order=order,
            )
        )
    return cells


def design_summary(cells: list[DesignCell]) -> dict[str, Any]:
    """Return auditable counts and factor levels for a design."""
    if not cells:
        return {"n": 0, "factors": {}, "blocks": 0, "replicates": 0}
    names = list(cells[0].factors)
    return {
        "n": len(cells),
        "factors": {name: sorted({str(c.factors[name]) for c in cells}) for name in names},
        "blocks": len({c.block for c in cells}),
        "replicates": len({c.replicate for c in cells}),
        "cell_ids_unique": len({c.cell_id for c in cells}) == len(cells),
    }
