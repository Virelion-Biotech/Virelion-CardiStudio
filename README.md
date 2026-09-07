# Virelion CardiStudio

CardiStudio is a Python toolkit for cardiac experimental design, synthetic population generation, constraint checking, power planning, and reproducible computational study specifications.

## Core capabilities

- Reproducible synthetic cardiac populations with deterministic seeds and provenance fingerprints
- Continuous, integer, binary, and categorical feature distributions
- Full-factorial experimental designs with replicates, blocks, and randomization
- Correlated multivariate sampling through validated Gaussian-copula latent variables
- Longitudinal recovery and transition trajectories
- Hard and soft row-level biological constraints
- Cohort validation and balance reports
- Effect-size and approximate two-arm power/sample-size planning
- JSON/JSONL serialization and versioned challenge specifications
- Streamlit interactive studio and CLI

## Example

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

## Architecture

`Design specification → Design engine → Population generator → Constraint engine → Analysis/provenance`

The package is deterministic where possible: seeds, canonical serialization, population fingerprints, and explicit design metadata make computational experiments auditable and reproducible.

## Scientific scope

CardiStudio generates **computational experimental designs and synthetic populations**. Generated values are simulations, not biological measurements and must not be represented as real patient, animal, or cell data.

## Development

```bash
pip install -e '.[dev]'
pytest -q
streamlit run app/streamlit_app.py
```

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See `LICENSE`.

## Citation

Cite the repository release and the datasets, assumptions, or experimental methods used to define or validate a computational study.
