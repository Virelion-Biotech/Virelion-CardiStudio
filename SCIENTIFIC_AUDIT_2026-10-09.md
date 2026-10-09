# Scientific audit changes — 2026-10-09

## Behavior

Add reproducible simulation_power callbacks and a Wilson Monte Carlo sampling interval, including boundary rejection rates.

## Scope and remaining evidence

Caller callbacks must implement hierarchy, longitudinal effects, missingness and the planned test correctly. This helper is not a validated default power workflow or a guarantee of clinical trial power.

## Implementation

- `tests/test_simulation_power.py`
- `src/cardistudio/power.py`

## Verification

Regression tests accompany the changes. Repository test results are recorded in the audit completion report and draft pull request. Software regression checks do not establish numerical, biological, transport or clinical validity.
