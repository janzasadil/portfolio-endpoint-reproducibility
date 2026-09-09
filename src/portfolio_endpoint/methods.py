"""Frozen headline portfolio target-weight rules and solver validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf


class OptimizationFailure(RuntimeError):
    """Raised when a required portfolio optimization has no valid solution."""


@dataclass(frozen=True)
class SolverSettings:
    feasibility_tolerance: float = 1e-8
    objective_tolerance: float = 1e-10
    erc_relative_tolerance: float = 1e-6
    erc_objective_tolerance: float = 1e-15
    max_iterations: int = 2_000


SETTINGS = SolverSettings()


def sample_covariance(history: np.ndarray) -> np.ndarray:
    covariance = np.cov(history, rowvar=False, ddof=1)
    if not np.isfinite(covariance).all():
        raise OptimizationFailure("Sample covariance is nonfinite")
    return np.atleast_2d(covariance)


def _validate_weights(weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    if not np.isfinite(weights).all():
        raise OptimizationFailure("Optimizer returned nonfinite weights")
    if abs(weights.sum() - 1.0) > SETTINGS.feasibility_tolerance:
        raise OptimizationFailure("Portfolio is not fully invested")
    if weights.min() < -SETTINGS.feasibility_tolerance:
        raise OptimizationFailure("Portfolio violates the long-only constraint")
    if not np.isfinite(weights @ covariance @ weights):
        raise OptimizationFailure("Portfolio objective is invalid")
    return np.maximum(weights, 0.0) / np.maximum(weights, 0.0).sum()


def long_only_gmv(covariance: np.ndarray) -> np.ndarray:
    """Solve the frozen long-only, fully-invested GMV allocation."""
    n_assets = covariance.shape[0]
    initial = np.full(n_assets, 1.0 / n_assets)
    result = minimize(
        fun=lambda weight: float(weight @ covariance @ weight),
        x0=initial,
        jac=lambda weight: 2.0 * covariance @ weight,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n_assets,
        constraints={"type": "eq", "fun": lambda weight: weight.sum() - 1.0,
                     "jac": lambda weight: np.ones(n_assets)},
        options={"ftol": SETTINGS.objective_tolerance, "maxiter": SETTINGS.max_iterations},
    )
    if not result.success:
        raise OptimizationFailure(f"GMV optimization failed: {result.message}")
    return _validate_weights(np.asarray(result.x), covariance)


def equal_weight(history: np.ndarray) -> np.ndarray:
    return np.full(history.shape[1], 1.0 / history.shape[1])


def sample_gmv(history: np.ndarray) -> np.ndarray:
    return long_only_gmv(sample_covariance(history))


def ledoit_wolf_gmv(history: np.ndarray) -> np.ndarray:
    covariance = LedoitWolf(assume_centered=False, store_precision=False).fit(history).covariance_
    if not np.isfinite(covariance).all():
        raise OptimizationFailure("Ledoit--Wolf covariance is nonfinite")
    return long_only_gmv(covariance)


def inverse_volatility(history: np.ndarray) -> np.ndarray:
    volatility = np.std(history, axis=0, ddof=1)
    if not np.isfinite(volatility).all() or np.any(volatility <= 0.0):
        raise OptimizationFailure("Inverse-volatility rule received an invalid volatility")
    inverse = 1.0 / volatility
    return inverse / inverse.sum()


def erc(history: np.ndarray) -> np.ndarray:
    """Solve the convex equal-risk-contribution risk-budgeting formulation."""
    covariance = sample_covariance(history)
    n_assets = covariance.shape[0]
    budget = 1.0 / n_assets
    # Positivity bounds make the logarithmic barrier well-defined.
    result = minimize(
        fun=lambda x: 0.5 * float(x @ covariance @ x) - budget * np.log(x).sum(),
        x0=np.full(n_assets, 1.0),
        jac=lambda x: covariance @ x - budget / x,
        method="L-BFGS-B",
        bounds=[(1e-12, None)] * n_assets,
        options={"ftol": SETTINGS.erc_objective_tolerance, "gtol": SETTINGS.objective_tolerance,
                 "maxiter": SETTINGS.max_iterations, "maxls": 100},
    )
    if not result.success:
        raise OptimizationFailure(f"ERC optimization failed: {result.message}")
    weights = np.asarray(result.x) / np.asarray(result.x).sum()
    weights = _validate_weights(weights, covariance)
    contribution = weights * (covariance @ weights)
    target = float(weights @ covariance @ weights) / n_assets
    if np.max(np.abs(contribution - target)) > SETTINGS.erc_relative_tolerance * max(target, 1e-16):
        raise OptimizationFailure("ERC solution fails the risk-budget validation")
    return weights


HEADLINE_METHODS = {
    "equal_weight": equal_weight,
    "sample_gmv": sample_gmv,
    "ledoit_wolf_gmv": ledoit_wolf_gmv,
    "inverse_volatility": inverse_volatility,
    "erc": erc,
}
