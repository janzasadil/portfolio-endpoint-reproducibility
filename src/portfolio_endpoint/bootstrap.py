"""Corrected Politis--White selection and circular stationary bootstrap."""

from __future__ import annotations

import math

import numpy as np


def corrected_pw_stationary_block_length(series: np.ndarray) -> int:
    """Select and bound the stationary-bootstrap mean block length.

    Implements the corrected Politis--White plug-in rule used by the frozen
    protocol, then applies its study-specific [2, floor(sqrt(T))] bound.
    """
    x = np.asarray(series, dtype=float)
    if x.ndim != 1 or len(x) < 10 or not np.isfinite(x).all():
        raise ValueError("Block-length selection requires a finite one-dimensional series")
    nobs = len(x)
    eps = x - x.mean()
    if np.allclose(eps, 0.0):
        return 2
    kn = max(5, int(math.log10(nobs)))
    m_max = math.ceil(math.sqrt(nobs)) + kn
    critical_value = 2.0 * math.sqrt(math.log10(nobs) / nobs)
    autocovariances = np.empty(m_max + 1)
    insignificant_start: int | None = None
    for lag in range(m_max + 1):
        cross_product = float(eps[lag:] @ eps[: nobs - lag])
        autocovariances[lag] = cross_product / nobs
        if lag >= kn:
            denominator = float(np.sqrt((eps[lag + 1 :] @ eps[lag + 1 :]) *
                                        (eps[: -(lag + 1)] @ eps[: -(lag + 1)])))
            autocorrelation = abs(cross_product) / denominator if denominator else math.inf
            # Check the most recent k_n autocorrelations, using the same
            # conservative band as the corrected selector.
            recent = []
            for prior_lag in range(lag - kn, lag):
                prior_cross = float(eps[prior_lag:] @ eps[: nobs - prior_lag])
                prior_denom = float(np.sqrt((eps[prior_lag + 1 :] @ eps[prior_lag + 1 :]) *
                                            (eps[: -(prior_lag + 1)] @ eps[: -(prior_lag + 1)])))
                recent.append(abs(prior_cross) / prior_denom if prior_denom else math.inf)
            if all(value < critical_value for value in recent) and insignificant_start is None:
                insignificant_start = lag - kn
    bandwidth = min(2 * max(insignificant_start or 1, 1), m_max)
    long_run_covariance = autocovariances[0]
    g = 0.0
    for lag in range(1, bandwidth + 1):
        kernel = 1.0 if lag / bandwidth <= 0.5 else 2.0 * (1.0 - lag / bandwidth)
        g += 2.0 * kernel * lag * autocovariances[lag]
        long_run_covariance += 2.0 * kernel * autocovariances[lag]
    if long_run_covariance == 0.0:
        candidate = 2.0
    else:
        candidate = ((2.0 * g**2) / (2.0 * long_run_covariance**2) * nobs) ** (1.0 / 3.0)
    return int(min(max(math.ceil(candidate), 2), math.floor(math.sqrt(nobs))))


def protocol_block_length(asset_returns: np.ndarray) -> int:
    """Use the larger corrected-PW value for EW raw returns and their squares."""
    matrix = np.asarray(asset_returns, dtype=float)
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ValueError("Asset returns must be a finite synchronized matrix")
    equal_weight_raw = matrix.mean(axis=1)
    return max(
        corrected_pw_stationary_block_length(equal_weight_raw),
        corrected_pw_stationary_block_length((equal_weight_raw - equal_weight_raw.mean()) ** 2),
    )


def stationary_indices(nobs: int, expected_block_length: int, rng: np.random.Generator) -> np.ndarray:
    """Generate circular stationary-bootstrap indices with geometric blocks."""
    if nobs < 1 or expected_block_length < 1:
        raise ValueError("nobs and expected block length must be positive")
    indices = np.empty(nobs, dtype=int)
    indices[0] = rng.integers(nobs)
    restart_probability = 1.0 / expected_block_length
    for position in range(1, nobs):
        if rng.random() < restart_probability:
            indices[position] = rng.integers(nobs)
        else:
            indices[position] = (indices[position - 1] + 1) % nobs
    return indices
