# Virelion CardiStudio

CardiStudio is a reproducible Python toolkit for experimental design, synthetic cardiac population generation, constraint-aware sampling, power planning, and computational study specifications.

## What it does

- Generates synthetic cohorts with explicit group effects and a recorded ground truth.
- Samples correlated continuous features through a validated Gaussian copula.
- Models biological hierarchy as subject → section/ROI → observation with subject-level random effects and ICC.
- Samples bounded normal/lognormal marginals by truncated distributions rather than clipping.
- Stores deterministic identifiers, generation metadata, and population fingerprints.
- Represents portable biological constraints as declarative relation expressions.
- Provides factorial design utilities with hashed cell identifiers.
- Provides subject-attached longitudinal trajectory generation and ICC-aware two-arm sample-size planning.
- Exports JSON, JSONL, CSV, and CardiBridge payloads.

Synthetic outputs are simulations, not empirical patient, animal, or cell measurements.

The CPU audit, numerical results, validation scope, and migration notes are in [validation/README.md](validation/README.md).

## Installation

```bash
pip install -e '.[dev,app]'
streamlit run app/streamlit_app.py
```

## Example

```python
from cardistudio import PopulationBuilder, approximate_two_sample_n
from cardistudio.presets import cardiac_mi_vs_sham

spec = cardiac_mi_vs_sham(n=4000, seed=2026)
population = PopulationBuilder(spec).build()

print(population.provenance["ground_truth"])
print(approximate_two_sample_n(0.5, cluster_size=10, icc=0.35))
```

The built-in MI-vs-sham preset contains explicit effects for ejection fraction, fibrosis, heart rate, and inflammation, correlated latent features, and nested biological replicates. This is intended as a pipeline benchmark, not a clinical or preclinical evidence model.

## Reproducibility

The population rows are generated from the challenge specification and seed. The provenance record includes the challenge fingerprint, generator version, hierarchy settings, truncation mass removed by bounds, configured effects, target correlation, and a SHA-256 fingerprint of the generated rows.

Bounded sampling was corrected in 0.3.0, so affected seeded populations must be regenerated. Pin generator and numerical dependency versions for reproducible benchmarks. Creation timestamps are not deterministic.

The generator's version is read from installed package metadata, so provenance does not depend on a duplicated hardcoded release string.

Verified population loading requires the JSONL and its `.provenance.json` sidecar.
Use `load_population(path, verify_provenance=False)` only for deliberate standalone
JSONL loading without digest verification.

For CardiBridge transport, use `cardi_bridge_envelope(spec, population)` or
`export_cardi_bridge_envelope(spec, population, path)`. The legacy
`export_cardi_bridge` exports a CardiStudio study bundle.

Configured ICC and correlation are latent Gaussian parameters. Transforms, rounding,
truncation and constraints can change observed statistics. Sections identify nested
observations but do not introduce another random effect.

## Constraints

Challenge files support declarative relation constraints such as:

```json
{
  "name": "ef_fibrosis_coherence",
  "type": "relation",
  "expr": "ejection_fraction < 0.4 implies fibrosis_fraction > 0.15",
  "severity": "error"
}
```

Constraints are parsed into a restricted expression language and enforced during generation by resampling violating observations while preserving subject-level random effects.

## Power planning

`approximate_two_sample_n` is a normal-approximation planning function. When observations are clustered within biological replicates, it applies the design-effect inflation:

```
DE = 1 + (m - 1) * ICC
```

It is not a substitute for the final analysis model.

## Validation

```bash
pytest
ruff check .
python -m mypy src
python -m compileall src app
python validation/run_cpu_validation.py
```

The test suite checks statistical behavior, hierarchy, truncation behavior, correlation recovery, constraint enforcement, schema migration, deterministic IDs, I/O, and power inflation.

## Limitations

Synthetic realism is limited by the distributions, effect assumptions, correlation structure, hierarchy, and constraints specified by the user. Constraint satisfaction does not establish biological validity. The ICC-aware power helper is an approximate planning aid and does not model every clustered or repeated-measures design.

Generated data must not be presented as empirical observations.

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See `LICENSE`.

## Citation

See `CITATION.cff`.
