from __future__ import annotations

from ..models import ChallengeSpec, FeatureSpec, PopulationSpec


def cardiac_mi_vs_sham(n: int = 1000, seed: int = 42) -> ChallengeSpec:
    """Reproducible synthetic mouse MI-vs-sham benchmark with known signal."""
    if n < 2:
        raise ValueError("n must be at least 2")
    sham = n // 2
    mi = n - sham
    corr_features = [
        "age_days",
        "heart_rate",
        "ejection_fraction",
        "fibrosis_fraction",
        "inflammation_score",
    ]
    return ChallengeSpec(
        name="cardiac-mi-vs-sham-demo",
        version="1.1",
        domain="cardiac",
        description=(
            "Synthetic MI-versus-sham benchmark population. Effects, correlation, "
            "and biological hierarchy are explicit so downstream methods have known truth."
        ),
        population=PopulationSpec(
            n=n,
            groups={"sham": sham, "mi": mi},
            group_field="condition",
            biological_replicates=20,
            sections_per_subject=4,
            intraclass_correlation=0.35,
            subject_field="subject_id",
            section_field="section_id",
            observation_field="observation_id",
            copula_features=corr_features,
            correlation=[
                [1.00, 0.10, -0.05, 0.00, 0.05],
                [0.10, 1.00, -0.20, 0.10, 0.25],
                [-0.05, -0.20, 1.00, -0.55, -0.40],
                [0.00, 0.10, -0.55, 1.00, 0.50],
                [0.05, 0.25, -0.40, 0.50, 1.00],
            ],
            seed=seed,
        ),
        features=[
            FeatureSpec(
                "age_days", "integer", "normal",
                {"mean": 56, "sd": 3}, "days",
                min_value=42, max_value=70,
            ),
            FeatureSpec(
                "heart_rate", "continuous", "normal",
                {"mean": 420, "sd": 35}, "bpm",
                min_value=250, max_value=550,
                effects={"mi": {"shift": 15.0, "scale": 1.0}},
            ),
            FeatureSpec(
                "ejection_fraction", "continuous", "normal",
                {"mean": 0.62, "sd": 0.06}, "fraction",
                min_value=0.2, max_value=0.85,
                effects={"mi": {"shift": -0.22, "scale": 1.15}},
            ),
            FeatureSpec(
                "fibrosis_fraction", "continuous", "normal",
                {"mean": 0.08, "sd": 0.025}, "fraction",
                min_value=0.0, max_value=0.5,
                effects={"mi": {"shift": 0.10, "scale": 1.20}},
            ),
            FeatureSpec(
                "inflammation_score", "continuous", "normal",
                {"mean": 0.0, "sd": 1.0}, "z",
                min_value=-4, max_value=4,
                effects={"mi": {"shift": 1.25, "scale": 1.20}},
            ),
        ],
        metadata={
            "species": "mouse",
            "injury": "myocardial_infarction",
            "control": "sham",
            "synthetic": True,
            "design_role": "benchmark",
        },
    )
