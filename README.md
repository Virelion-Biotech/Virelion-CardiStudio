# Virelion CardiStudio

**Cardiac experimental-population design, simulation, constraint checking, power planning and reproducibility engine.**

CardiStudio is the design layer of the Virelion cardiac-computation stack. It turns an experimental hypothesis into a structured, reproducible population/design specification that can be consumed by downstream simulation, evaluation and learning systems.

## Core capabilities

- Reproducible synthetic cardiac populations with deterministic seeds and provenance fingerprints
- Continuous, integer, binary and categorical feature distributions
- Full-factorial experimental designs with replicates, blocks and randomization
- Correlated multivariate sampling through validated Gaussian-copula latent variables
- Longitudinal recovery/transition trajectories
- Hard and soft row-level biological constraints
- Cohort validation and balance reports
- Effect-size and approximate two-arm power/sample-size planning
- JSON/JSONL interoperability and versioned challenge schemas
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

`ChallengeSpec → Design Engine → Population Generator → Constraint Engine → Analysis/Provenance → CardiBridge/CardiEval/CardiLearn`

The package is deliberately deterministic where possible: seeds, canonical challenge serialization, population fingerprints and explicit design metadata make synthetic experiments auditable and reproducible.

## Scientific scope

CardiStudio generates **computational experimental designs and synthetic populations**. Generated values are simulations, not biological measurements and must not be represented as real patient/animal/cell data.

## Development

```bash
pip install -e .
pytest -q
streamlit run app/streamlit_app.py
```
