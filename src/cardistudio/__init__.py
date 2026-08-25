"""CardiStudio: reproducible cardiac experimental-population design and simulation."""
from .models import ChallengeSpec, FeatureSpec, PopulationSpec
from .population import PopulationBuilder, Population
from .validation import ValidationReport, validate_challenge, validate_population
from .analysis import summarize_population, balance_report
from .io import load_challenge, save_challenge, save_population, load_population
from .design import Factor, ExperimentalDesign, full_factorial
from .correlations import gaussian_copula, correlated_normals
from .trajectory import TrajectorySpec, exponential_recovery, logistic_transition
from .constraints import Constraint, ConstraintEngine, ConstraintReport, range_constraint, relationship_constraint
from .power import cohens_d, approximate_two_sample_n

__all__ = [
    "ChallengeSpec", "FeatureSpec", "PopulationSpec", "PopulationBuilder", "Population",
    "ValidationReport", "validate_challenge", "validate_population", "summarize_population",
    "balance_report", "load_challenge", "save_challenge", "save_population", "load_population",
    "Factor", "ExperimentalDesign", "full_factorial", "gaussian_copula", "correlated_normals",
    "TrajectorySpec", "exponential_recovery", "logistic_transition", "Constraint", "ConstraintEngine",
    "ConstraintReport", "range_constraint", "relationship_constraint", "cohens_d", "approximate_two_sample_n",
]
