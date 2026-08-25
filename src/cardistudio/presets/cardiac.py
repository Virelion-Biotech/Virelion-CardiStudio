from __future__ import annotations

from ..models import ChallengeSpec, FeatureSpec, PopulationSpec


def cardiac_mi_vs_sham(n: int = 1000, seed: int = 42) -> ChallengeSpec:
    """Return a reproducible synthetic mouse MI-vs-sham design."""
    if n < 2:
        raise ValueError("n must be at least 2")
    sham = n // 2
    mi = n - sham
    return ChallengeSpec(
        name="cardiac-mi-vs-sham-demo",
        version="1.1",
        domain="cardiac",
        description="Synthetic MI-versus-sham study population for pipeline testing.",
        population=PopulationSpec(
            n=n,
            groups={"sham": sham, "mi": mi},
            group_field="condition",
            biological_replicates=5,
            seed=seed,
        ),
        features=[
            FeatureSpec("age_days", "integer", "normal", {"mean": 56, "sd": 3}, "days", min_value=42, max_value=70),
            FeatureSpec("heart_rate", "continuous", "normal", {"mean": 420, "sd": 35}, "bpm", min_value=250, max_value=550),
            FeatureSpec("ejection_fraction", "continuous", "normal", {"mean": 0.62, "sd": 0.06}, "fraction", min_value=.2, max_value=.85),
            FeatureSpec("fibrosis_fraction", "continuous", "normal", {"mean": .08, "sd": .025}, "fraction", min_value=0, max_value=.5),
            FeatureSpec("inflammation_score", "continuous", "normal", {"mean": 0, "sd": 1}, "z", min_value=-4, max_value=4),
        ],
        metadata={
            "species": "mouse",
            "injury": "myocardial_infarction",
            "control": "sham",
            "synthetic": True,
            "design_role": "pipeline_testing",
        },
    )
