# CardiStudio 0.3.0 CPU audit — 2026-10-07

## Scope and evidence

This audit validates computational behavior and selected statistical properties on ordinary CPU hardware. It does not establish empirical validity of cardiac distributions, treatment effects, causal relationships, or clinical/preclinical outcomes. The MI-vs-sham preset is a synthetic pipeline benchmark with assumed parameters.

The original 24 tests passed (86.25% statement coverage). An initial set of 22 independent regression cases produced 20 failures. The repaired implementation passes 91 regression, property, UI and interoperability tests (88.66% statement coverage). Results and exact commands are recorded below; CI repeats the checks on Linux Python 3.10–3.14 and Windows Python 3.12, with a separate minimum-dependency and installed-wheel job.

## Confirmed defects repaired

- Bounded normal and lognormal sampling mapped quantiles into the truncation interval twice. Passing uniform quantiles directly to the conditional inverse CDF restores the intended distributions, including a normal truncated to [20,21].
- Integer rounding could violate nonintegral bounds. Rounded latent distributions now condition on the allowed integer rounding cells.
- Invalid distributions, parameters, reserved names, hierarchy identities and unsupported effects could reach generation. Schema and semantic validation now run before sampling and on generated rows.
- Reusing a builder advanced structural RNG state; source-spec mutation also changed the builder. Generation now restarts its seed and detaches the input specification.
- Boolean constraint evaluation did not short-circuit implication. Parsing, arithmetic and finite-value checks now reject unsupported or undefined expressions.
- Loaded population files were not checked against their recorded digest. Verified loading requires the provenance sidecar, checks SHA-256 and row counts, and rejects nonfinite or duplicate-key JSON.
- Constant values and mixed categorical labels could produce invalid or ambiguous outputs. Constants are checked against bounds/effects; category types are preserved and count keys use canonical JSON scalar encodings.
- Trajectory parameters and power inputs accepted nonfinite values. Recovery rates with nonzero variability now follow a positive truncated normal instead of accumulating clipped rates at a floor. Logistic and recovery interpolation avoid avoidable overflow.
- The old CardiBridge export was a CardiStudio study bundle. The new `cardi_bridge_envelope`/`export_cardi_bridge_envelope` APIs produce a canonical `agent.challenge` envelope verified against actual CardiBridge contracts at revision `fc990ace415c97fb301b2386066862b3dfe8ae98`.
- The app conflated observations and subjects, accepted uploads through a JSON reserialization step that erased duplicate keys, omitted provenance downloads and displayed changed settings alongside an old cohort without notice. These paths are corrected; generic numeric feature plotting and the bridge envelope download are added.
- The original empirical ICC check pooled treatment groups and used an invalid ICC formula. Validation now uses balanced one-way ANOVA within homogeneous groups.

## Independent statistical experiments

`results.json` records the environment, seeds, sample sizes, thresholds and numerical outcomes. Reproduce with:

```bash
python -m pip install -e '.[dev,app]'
python validation/run_cpu_validation.py --output validation/results.json
python -m pytest
python -m ruff check .
python -m mypy src
python -m build
```

Six marginals are tested against analytical CDFs at three seeds each: normal, bounded normal, extreme-tail normal, bounded uniform, lognormal and bounded lognormal. Each run uses 4,000 independent observations. The maximum Kolmogorov–Smirnov distance is approximately 0.01642, below the predetermined 0.035 threshold. Shared seeds intentionally yield the same probability-scale draws across these transformations; these are transformation checks, not 18 independent random experiments.

Hierarchy experiments use 1,000 subjects, six observations per subject, three seeds and unbounded normal marginals. Mean balanced-ANOVA ICC estimates are approximately −0.00667, 0.35040 and 0.80011 for targets 0, 0.35 and 0.8. Negative finite-sample estimates at the zero target are retained. Normal-feature correlations recover the target 0.65 within the specified 0.05 tolerance.

A 100,000-trial simulation of independent known-variance z-tests gives power 0.79971 at effect size 0.5 and 63 observations per arm. This validates the stated normal approximation; it does not validate small-sample t-tests, cluster-randomized trials or mixed-model inference.

Primary mathematical references:

- [SciPy truncated normal distribution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.truncnorm.html): standardized truncation limits and conditional inverse CDF.
- [SciPy lognormal distribution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.lognorm.html): log-space parameterization.
- [Statsmodels normal-approximation power](https://www.statsmodels.org/stable/generated/statsmodels.stats.power.NormalIndPower.html): independent two-sample normal planning scope.

## Interpretation and migration

Version 0.3.0 intentionally changes seeded outputs where bounded distributions, integer bounds or variable recovery rates are involved. Regenerate affected benchmark data and retain package, NumPy and SciPy versions alongside the specification and seed. Reproducibility covers rows for the same environment and inputs; creation timestamps vary. Byte-for-byte equality across dependency versions is not promised.

The configured matrix and ICC apply to latent Gaussian variables. Nonlinear transforms, rounding, truncation and constraint rejection can change observed Pearson correlations and ICC. Provenance distinguishes assumed pre-truncation/pre-constraint parameters from realized sample statistics. The section identifier is an indexing layer; no independent section-level random effect is modeled. The constraint solver uses at most 100 rejection rounds and can fail when a condition has insufficient conditional support. Warning constraints report violations without changing draws.

`load_population(path)` now requires `population.jsonl.provenance.json`. Deliberately loading an unverified standalone JSONL requires `verify_provenance=False`, which still enforces finite JSON and synthetic row markers. Each saved file is replaced atomically; the two-file pair is not a single transaction. A mismatched pair fails verification. Hashes detect inconsistency, not authorship or malicious replacement of both files.

The legacy `export_cardi_bridge` remains a CardiStudio study bundle. Use the new envelope API for CardiBridge transport. Envelope identity is deterministic for challenge, row digest and consumer; generation timestamps differ between independent builds. Full challenge constraints and provenance are retained in the trace. This audit verifies contract compatibility, not deployment, authentication or delivery to a live consumer.

Population size is observations. Actual subjects per group are `min(biological_replicates, group_count)` and are recorded in provenance. The power helper returns approximate observations per arm, not independent subjects; clustered designs require an appropriate final analysis and cluster-count rounding.
