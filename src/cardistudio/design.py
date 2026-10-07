from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from .serialization import canonical_json
from itertools import product
from typing import Any
import hashlib
import math


@dataclass(frozen=True)
class Factor:
    name: str
    levels: tuple[Any, ...]


@dataclass
class ExperimentalDesign:
    factors: list[Factor]
    replicates: int = 1
    blocks: int = 1
    randomize: bool = True
    seed: int = 42
    rows: list[dict[str, Any]] = field(default_factory=list)

    def generate(self) -> list[dict[str, Any]]:
        if (
            type(self.replicates) is not int
            or type(self.blocks) is not int
            or self.replicates < 1
            or self.blocks < 1
        ):
            raise ValueError("replicates and blocks must be >= 1")
        if not self.factors or any(not f.levels for f in self.factors):
            raise ValueError("At least one factor with levels is required")
        factor_names = [f.name for f in self.factors]
        if len(set(factor_names)) != len(factor_names) or any(
            not name.strip() or name in {"block", "replicate", "cell_id", "design_id"}
            for name in factor_names
        ):
            raise ValueError("Factor names must be nonempty, distinct, and not reserved")
        for factor in self.factors:
            labels = [canonical_json(value) for value in factor.levels]
            if len(set(labels)) != len(labels):
                raise ValueError("Factor levels must be distinct")
        cells = [
            dict(zip(factor_names, levels)) for levels in product(*(f.levels for f in self.factors))
        ]
        rows = []
        for block in range(1, self.blocks + 1):
            for rep in range(1, self.replicates + 1):
                for cell in cells:
                    row = dict(deepcopy(cell), block=block, replicate=rep)
                    canonical = canonical_json(
                        {"factors": cell, "block": block, "replicate": rep, "seed": self.seed}
                    )
                    row["cell_id"] = hashlib.sha256(canonical.encode()).hexdigest()[:16]
                    row["design_id"] = row["cell_id"]
                    rows.append(row)
        if self.randomize:
            import random

            rng = random.Random(self.seed)
            rng.shuffle(rows)
        self.rows = rows
        return rows

    @property
    def n_runs(self) -> int:
        return math.prod(len(f.levels) for f in self.factors) * self.replicates * self.blocks

    @property
    def n_factorial_cells(self) -> int:
        return math.prod(len(f.levels) for f in self.factors)


def full_factorial(
    factors: dict[str, list[Any]],
    replicates: int = 1,
    blocks: int = 1,
    seed: int = 42,
) -> ExperimentalDesign:
    d = ExperimentalDesign(
        [Factor(k, tuple(v)) for k, v in factors.items()],
        replicates,
        blocks,
        True,
        seed,
    )
    d.generate()
    return d
