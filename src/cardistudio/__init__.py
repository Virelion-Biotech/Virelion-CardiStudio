"""CardiStudio: reproducible cardiac experimental-population design and simulation."""
from importlib.metadata import PackageNotFoundError, version

from .models import ChallengeSpec, FeatureSpec, PopulationSpec, CURRENT_CHALLENGE_VERSION
from .population import PopulationBuilder, Population, GENERATOR_VERSION
from .validation import ValidationReport, validate_challenge, validate_population
from .analysis import summarize_population, balance_report
from .io import (\n    export_cardi_bridge,\n    load_challenge,\n    load_population,\n    save_challenge,\n    save_population,\n)
from .design import Factor, ExperimentalDesign, full_factorial
from .correlations import gaussian_copula, correlated_normals, validate_correlation
from .trajectory import (
    TrajectorySpec,
    exponential_recovery,
    logistic_transition,
    subject_exponential_long,
)
from .constraints import (
    Constraint,
    ConstraintEngine,
    ConstraintReport,
    range_constraint,
    relationship_constraint,
    declarative_constraint,
)
from .power import cohens_d, approximate_two_sample_n

try:
    __version__ = version("virelion-cardistudio")
except PackageNotFoundError:
    __version__ = "0+local"

__all__ = [
    "ChallengeSpec", "FeatureSpec", "PopulationSpec", "CURRENT_CHALLENGE_VERSION",
    "PopulationBuilder", "Population", "GENERATOR_VERSION", "ValidationReport",
    "validate_challenge", "validate_population", "summarize_population", "balance_report",
    "load_challenge", "save_challenge", "save_population", "load_population",
    "export_cardi_bridge", "Factor", "ExperimentalDesign", "full_factorial",
    "gaussian_copula", "correlated_normals", "validate_correlation", "TrajectorySpec",
    "exponential_recovery", "logistic_transition", "subject_exponential_long",
    "Constraint", "ConstraintEngine", "ConstraintReport", "range_constraint",
    "relationship_constraint", "declarative_constraint", "cohens_d",
    "approximate_two_sample_n", "__version__",
]
