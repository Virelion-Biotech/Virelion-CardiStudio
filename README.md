# CardiStudio

**Virelion-CardiStudio** is a reproducible cardiac challenge-population studio for defining, validating, sampling, exporting, and visualizing synthetic cardiac cohorts.

## Core capabilities

- Typed challenge specifications with schema validation
- Biological populations, phenotypes, perturbations, interventions, and metadata
- Correlated multi-axis population generation with reproducible seeds
- Constraint-aware sampling and rejection diagnostics
- CardiAgent-compatible challenge ingestion and export
- CardiVex observation export and CardiEval prediction/benchmark adapters
- JSON/JSONL/CSV export with provenance manifests and SHA-256 fingerprints
- Statistical summaries, cohort balance checks, and visualization-ready projections
- Optional Streamlit application for interactive cohort construction
- CLI for deterministic headless workflows

## Architecture

`ChallengeSpec -> PopulationBuilder -> Validator -> Analyzer -> Exporter -> downstream Cardi* tools`

The package is deliberately dependency-light. NumPy is the only runtime dependency; pandas, Plotly, and Streamlit are optional extras.

## Quick start

```bash
pip install -e '.[dev]'
cardistudio demo --seed 42 --n 500 --output artifacts/demo
cardistudio validate artifacts/demo/challenge.json
cardistudio summarize artifacts/demo/population.jsonl
```

## Design principles

1. **Reproducibility first** — every generated cohort records seed, specification hash, package version, and generation timestamp.
2. **Biological semantics over arbitrary random numbers** — variables have domains, units, distributions, and relationships.
3. **No silent leakage** — population IDs, biological groups, and split assignments are explicit.
4. **Interoperability** — stable JSON schemas make CardiStudio usable by CardiAgent, CardiVex, CardiLearn, CardiEval, CardiSim, and CardiTrace.
5. **Research transparency** — validation diagnostics are exported alongside data rather than hidden in the UI.

## Status

This repository contains the complete initial production architecture and an executable reference implementation. It is a simulation/study-design tool, not a clinical decision system.

## License

MIT.
