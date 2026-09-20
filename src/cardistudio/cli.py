from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import summarize_population
from .io import (
    export_cardi_bridge,
    load_challenge,
    load_population,
    save_challenge,
    save_csv,
    save_population,
)
from .population import PopulationBuilder
from .presets import cardiac_mi_vs_sham
from .validation import validate_challenge


def main() -> None:
    parser = argparse.ArgumentParser(prog="cardistudio")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    demo = subparsers.add_parser("demo")
    demo.add_argument("--n", type=int, default=1000)
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--output", default="artifacts/demo")

    validate = subparsers.add_parser("validate")
    validate.add_argument("path")

    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("path")

    args = parser.parse_args()

    if args.cmd == "demo":
        spec = cardiac_mi_vs_sham(args.n, args.seed)
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        population = PopulationBuilder(spec).build()
        save_challenge(spec, output / "challenge.json")
        save_population(population, output / "population.jsonl")
        save_csv(population.rows, output / "population.csv")
        export_cardi_bridge(spec, population, output / "cardi_bridge.json")
        (output / "summary.json").write_text(
            json.dumps(summarize_population(population.rows), indent=2),
            encoding="utf-8",
        )
        print(
            f"Generated {len(population.rows)} rows at {output} | "
            f"fingerprint={spec.fingerprint()}"
        )
    elif args.cmd == "validate":
        spec = load_challenge(args.path)
        report = validate_challenge(spec)
        print(json.dumps(report.__dict__, indent=2))
        report.raise_if_invalid()
    elif args.cmd == "summarize":
        print(json.dumps(summarize_population(load_population(args.path)), indent=2))


if __name__ == "__main__":
    main()
