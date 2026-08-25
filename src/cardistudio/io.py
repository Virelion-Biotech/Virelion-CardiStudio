from __future__ import annotations
import csv, json
from pathlib import Path
from .models import ChallengeSpec
from .population import Population

def save_challenge(spec: ChallengeSpec, path: str | Path):
    Path(path).write_text(json.dumps(spec.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

def load_challenge(path: str | Path) -> ChallengeSpec:
    return ChallengeSpec.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

def save_population(pop: Population, path: str | Path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pop.to_jsonl(), encoding="utf-8")
    path.with_suffix(path.suffix + ".provenance.json").write_text(json.dumps(pop.provenance, indent=2, sort_keys=True), encoding="utf-8")

def load_population(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def save_csv(rows: list[dict], path: str | Path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: path.write_text(""); return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def export_cardi_bridge(spec: ChallengeSpec, pop: Population, path: str | Path):
    payload = {"schema": "virelion.cardistudio.challenge.v1", "challenge": spec.to_dict(), "provenance": pop.provenance, "population": pop.rows}
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
