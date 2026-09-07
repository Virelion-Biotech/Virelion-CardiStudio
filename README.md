# Virelion CardiStudio

CardiStudio is a Python toolkit for cardiac experimental design, synthetic population generation, constraint checking, power planning, and reproducible computational study specifications.

## What it contains

- Reproducible synthetic cardiac populations with deterministic seeds and provenance fingerprints.
- Continuous, integer, binary, and categorical feature distributions.
- Full-factorial experimental designs with replicates, blocks, and randomization.
- Correlated multivariate sampling through validated Gaussian-copula latent variables.
- Longitudinal recovery and transition trajectories.
- Hard and soft row-level biological constraints.
- Cohort validation and balance reports.
- Effect-size and approximate two-arm power/sample-size planning.
- JSON/JSONL serialization and versioned challenge specifications.
- Streamlit interface and CLI.

## Installation

```bash
pip install -e '.[dev]'
```

## Usage

```python
from cardistudio import full_factorial, correlated_normals, approximate_two_sample_n

design = full_factorial(
    {"condition": ["sham", "MI"], "zone": ["remote", "border", "IZ"]},
    replicates=6,
    blocks=2,
    seed=2026,
)

physiology = correlated_normals(
    1000,
    means=[65, 55],
    sds=[8, 10],
    correlation=[[1, -0.55], [-0.55, 1]],
    seed=2026,
)

n_per_arm = approximate_two_sample_n(effect_size=0.5, alpha=0.05, power=0.8)
```

Development commands:

```bash
pytest -q
streamlit run app/streamlit_app.py
```

## Inputs and outputs

**Inputs:** factor definitions, replicate/block/randomization settings, feature distributions, correlation matrices, trajectory parameters, biological constraints, effect-size assumptions, alpha/power targets, and random seeds.

**Outputs:** experimental design tables, synthetic population tables, trajectory specifications, constraint/balance reports, power/sample-size estimates, JSON/JSONL study specifications, and provenance fingerprints.

Generated values are simulations, not patient, animal, or cell measurements.

## Validation

Validation includes design and population constraint checks, balance reports, deterministic-seed reproducibility, correlation-matrix validation, and software tests. Power calculations are approximate planning tools and should be checked against the intended statistical model.

## Limitations

Synthetic populations depend on the specified distributions, correlations, constraints, and assumptions. Constraint satisfaction does not establish biological realism. Approximate power calculations may differ from the final analysis model. Generated data must not be presented as empirical observations.

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See `LICENSE`.
