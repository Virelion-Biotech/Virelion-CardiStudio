# Changelog

## 0.3.0 - 2026-10-07

### Fixed
- Corrected doubly truncated normal/lognormal quantiles and extreme-tail sampling.
- Enforced integer support, finite parameters, distribution compatibility and hierarchy integrity.
- Restored repeatable builds and detached mutable input specifications.
- Added strict JSON, digest verification, provenance sidecars and atomic file replacement.
- Corrected implication evaluation, ICC validation and positive recovery-rate sampling.
- Preserved categorical scalar types and unambiguous recorded counts.
- Made CLI failures return nonzero status with actionable stderr.

### Added
- Canonical CardiBridge envelopes tested against actual pinned CardiBridge contracts.
- Streamlit subject counts, changed-settings notice, generic numeric plots and provenance downloads.
- CPU statistical validation report, property/regression/UI/integration tests, installed-wheel checks,
  minimum-dependency checks, Python 3.14 and Windows CI.

### Compatibility
- Corrected bounded/rounded distributions and variable recovery rates change seeded outputs.
- Verified population loading now requires the matching provenance sidecar.
- Unsupported minor schemas, invalid effects and nonfinite/duplicate-key JSON fail validation.
- Category count keys now encode JSON scalars to distinguish numeric and string labels.
- Streamlit app requires Streamlit 1.65 or newer; computational core dependencies are unchanged.

## 0.2.0 - 2026-09-20

### Changed
- Added first-class group-conditional feature effects and provenance ground truth.
- Wired Gaussian-copula latent correlation into population generation.
- Added subject/section/observation nesting and ICC-driven subject variance.
- Added ICC design-effect inflation to approximate two-sample sample-size planning.
- Replaced duplicate design/trajectory modules with the canonical implementations.
- Added executable declarative relation constraints and schema validation/migration.
- Added hashed design cell IDs and dynamic package-version provenance.
- Expanded behavioral tests and CI quality checks.
