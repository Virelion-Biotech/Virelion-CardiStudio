import argparse, json
from pathlib import Path
from .presets import cardiac_mi_vs_sham
from .population import PopulationBuilder
from .validation import validate_challenge, validate_population
from .io import load_challenge, load_population, save_challenge, save_population, save_csv
from .analysis import summarize_population

def main():
    p = argparse.ArgumentParser(prog="cardistudio")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo"); d.add_argument("--n", type=int, default=1000); d.add_argument("--seed", type=int, default=42); d.add_argument("--output", default="artifacts/demo")
    v = sub.add_parser("validate"); v.add_argument("path")
    s = sub.add_parser("summarize"); s.add_argument("path")
    a = p.parse_args()
    if a.cmd == "demo":
        spec = cardiac_mi_vs_sham(a.n, a.seed); out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
        pop = PopulationBuilder(spec).build(); save_challenge(spec, out/"challenge.json"); save_population(pop, out/"population.jsonl"); save_csv(pop.rows, out/"population.csv")
        (out/"summary.json").write_text(json.dumps(summarize_population(pop.rows), indent=2), encoding="utf-8")
        print(f"Generated {len(pop.rows)} rows at {out} | fingerprint={spec.fingerprint()}")
    elif a.cmd == "validate":
        spec = load_challenge(a.path); report = validate_challenge(spec); print(json.dumps(report.__dict__, indent=2)); report.raise_if_invalid()
    elif a.cmd == "summarize": print(json.dumps(summarize_population(load_population(a.path)), indent=2))

if __name__ == "__main__": main()
