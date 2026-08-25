from __future__ import annotations
from dataclasses import dataclass, field
from itertools import product
from typing import Any
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
        if self.replicates < 1 or self.blocks < 1:
            raise ValueError("replicates and blocks must be >= 1")
        if not self.factors or any(not f.levels for f in self.factors):
            raise ValueError("At least one factor with levels is required")
        cells = [dict(zip([f.name for f in self.factors], levels)) for levels in product(*[f.levels for f in self.factors])]
        rows = []
        for block in range(1, self.blocks + 1):
            for rep in range(1, self.replicates + 1):
                for cell in cells:
                    row = dict(cell, block=block, replicate=rep)
                    row["design_id"] = f"D-{len(rows)+1:06d}"
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


def full_factorial(factors: dict[str, list[Any]], replicates: int = 1, blocks: int = 1, seed: int = 42) -> ExperimentalDesign:
    d = ExperimentalDesign([Factor(k, tuple(v)) for k, v in factors.items()], replicates, blocks, True, seed)
    d.generate()
    return d
