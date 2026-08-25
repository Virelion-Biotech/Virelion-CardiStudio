from __future__ import annotations
import numpy as np


def gaussian_copula(n: int, correlation: list[list[float]], seed: int = 42) -> np.ndarray:
    """Sample correlated standard-normal latent variables with validation."""
    c = np.asarray(correlation, dtype=float)
    if c.ndim != 2 or c.shape[0] != c.shape[1]:
        raise ValueError("correlation must be square")
    if not np.allclose(c, c.T, atol=1e-8):
        raise ValueError("correlation matrix must be symmetric")
    if not np.allclose(np.diag(c), 1.0, atol=1e-8):
        raise ValueError("correlation diagonal must equal 1")
    if np.min(np.linalg.eigvalsh(c)) < -1e-8:
        raise ValueError("correlation matrix must be positive semidefinite")
    rng = np.random.default_rng(seed)
    return rng.multivariate_normal(np.zeros(c.shape[0]), c, size=n, check_valid="raise")


def correlated_normals(n: int, means: list[float], sds: list[float], correlation: list[list[float]], seed: int = 42) -> np.ndarray:
    if len(means) != len(sds) or len(means) != len(correlation):
        raise ValueError("means, sds and correlation dimensions must agree")
    if any(x <= 0 for x in sds):
        raise ValueError("all standard deviations must be > 0")
    z = gaussian_copula(n, correlation, seed)
    return z * np.asarray(sds) + np.asarray(means)
