"""Corrected Politis--White selection and circular stationary bootstrap."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pandas as pd

from .analysis import (
    TIE_BREAK_ORDER,
    candidate_return_matrix,
    ceq,
    endpoint_reproducibility,
    endpoint_summary,
    ex_ante_selection,
    kaplan_meier,
    survival_summary,
    winner_survival,
)
from .engine import PathResult, run_headline_paths


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


def stationary_resample(returns: pd.DataFrame, expected_block_length: int, rng: np.random.Generator) -> pd.DataFrame:
    """Resample whole monthly asset-return vectors while retaining calendar labels."""
    if returns.empty or returns.isna().any().any():
        raise ValueError("Bootstrap input must be a complete return matrix")
    indices = stationary_indices(len(returns), expected_block_length, rng)
    # Preserve the original dates: only return vectors, not the calendar needed
    # to identify December inferential origins, are resampled.
    return pd.DataFrame(returns.to_numpy()[indices], index=returns.index, columns=returns.columns)


def outer_bootstrap(
    returns: pd.DataFrame,
    *,
    replications: int = 5000,
    seed: int = 20260909,
    lookback: int = 60,
    transaction_cost: float = 0.0025,
    horizon: int = 120,
    displacement: int = 12,
    gamma: float = 5.0,
    start_replication: int = 0,
    checkpoint_every: int | None = None,
    checkpoint_callback: Callable[[pd.DataFrame], None] | None = None,
) -> pd.DataFrame:
    """Reconstruct the frozen primary statistics in stationary-bootstrap histories.

    The block length is estimated once from the original history, then fixed for
    all replications. This deliberately does not call an inner bootstrap.
    """
    if replications < 1:
        raise ValueError("At least one bootstrap replication is required")
    block_length = protocol_block_length(returns.to_numpy())
    records: list[dict[str, float | int]] = []
    for replication in range(start_replication, start_replication + replications):
        # A replication-specific stream makes chunks reproducible and resumable:
        # chunk boundaries cannot change any other replication's pseudo-history.
        rng = np.random.default_rng(np.random.SeedSequence([seed, replication]))
        pseudo_returns = stationary_resample(returns, block_length, rng)
        paths = run_headline_paths(pseudo_returns, lookback, transaction_cost)
        endpoints = endpoint_reproducibility(paths, horizon, displacement, gamma, december_only=True)
        endpoint_stats = endpoint_summary(endpoints)
        selections = ex_ante_selection(paths, horizon, gamma, december_only=True)
        survival = survival_summary(kaplan_meier(winner_survival(paths, horizon, gamma, december_only=True)))
        records.append({
            "replication": replication,
            "block_length": block_length,
            **endpoint_stats,
            "mean_selection_regret": float(selections["selection_regret"].mean()),
            "mean_selector_minus_ensemble": float(selections["selector_minus_ensemble"].mean()),
            "selector_hit_rate": float(selections["selector_hit"].mean()),
            "mean_selector_rank": float(selections["selector_rank"].mean()),
            **survival,
        })
        if checkpoint_callback and checkpoint_every and len(records) % checkpoint_every == 0:
            checkpoint_callback(pd.DataFrame.from_records(records))
    if checkpoint_callback:
        checkpoint_callback(pd.DataFrame.from_records(records))
    return pd.DataFrame.from_records(records)


def _paths_at_cost(paths: dict[str, PathResult], transaction_cost: float) -> dict[str, PathResult]:
    """Reprice fixed gross paths at a different proportional turnover cost."""
    repriced = {}
    for name, path in paths.items():
        net = (1.0 - transaction_cost * path.turnover) * (1.0 + path.gross_returns) - 1.0
        repriced[name] = PathResult(path.weights, path.gross_returns, net.rename("net_return"), path.turnover)
    return repriced


def _draw_metrics(paths: dict[str, PathResult], horizon: int, displacement: int, gamma: float) -> dict[str, float]:
    endpoints = endpoint_reproducibility(paths, horizon, displacement, gamma, december_only=True)
    selections = ex_ante_selection(paths, horizon, gamma, december_only=True)
    survival = survival_summary(kaplan_meier(winner_survival(paths, horizon, gamma, december_only=True)))
    return {
        **endpoint_summary(endpoints),
        "mean_selection_regret": float(selections["selection_regret"].mean()),
        "mean_selector_minus_ensemble": float(selections["selector_minus_ensemble"].mean()),
        "selector_hit_rate": float(selections["selector_hit"].mean()),
        "mean_selector_rank": float(selections["selector_rank"].mean()),
        **survival,
    }


def outer_sensitivity_bootstrap(
    returns: pd.DataFrame,
    *,
    replications: int = 2000,
    seed: int = 20260909,
    lookback: int = 60,
    transaction_cost: float = 0.0025,
    horizon: int = 120,
    displacement: int = 12,
    gamma: float = 5.0,
    start_replication: int = 0,
    checkpoint_every: int | None = None,
    checkpoint_callback: Callable[[pd.DataFrame], None] | None = None,
) -> pd.DataFrame:
    """Paired one-at-a-time h, H, gamma, and cost sensitivity draws.

    Every cell uses the identical pseudo-history within a replication. Lookback,
    rebalancing, fixed-block, and universe sensitivities intentionally remain
    outside this runner because they change portfolio construction or sampling.
    """
    block_length = protocol_block_length(returns.to_numpy())
    records: list[dict[str, float | int]] = []
    for replication in range(start_replication, start_replication + replications):
        rng = np.random.default_rng(np.random.SeedSequence([seed, replication]))
        pseudo_returns = stationary_resample(returns, block_length, rng)
        baseline_paths = run_headline_paths(pseudo_returns, lookback, transaction_cost)
        cells = {
            "baseline": (baseline_paths, horizon, displacement, gamma),
            "h6": (baseline_paths, horizon, 6, gamma),
            "h24": (baseline_paths, horizon, 24, gamma),
            "H5": (baseline_paths, 60, displacement, gamma),
            "H15": (baseline_paths, 180, displacement, gamma),
            "gamma2": (baseline_paths, horizon, displacement, 2.0),
            "gamma10": (baseline_paths, horizon, displacement, 10.0),
            "cost0": (_paths_at_cost(baseline_paths, 0.0), horizon, displacement, gamma),
            "cost50": (_paths_at_cost(baseline_paths, 0.005), horizon, displacement, gamma),
        }
        metrics = {name: _draw_metrics(*arguments) for name, arguments in cells.items()}
        record: dict[str, float | int] = {"replication": replication, "block_length": block_length}
        for name, values in metrics.items():
            record.update({f"{name}_{metric}": value for metric, value in values.items()})
        for name, values in metrics.items():
            if name != "baseline":
                record.update({f"delta_{name}_{metric}": value - metrics["baseline"][metric]
                               for metric, value in values.items()})
        records.append(record)
        if checkpoint_callback and checkpoint_every and len(records) % checkpoint_every == 0:
            checkpoint_callback(pd.DataFrame.from_records(records))
    if checkpoint_callback:
        checkpoint_callback(pd.DataFrame.from_records(records))
    return pd.DataFrame.from_records(records)


def percentile_interval(samples: pd.Series | np.ndarray, level: float = 0.95) -> tuple[float, float]:
    """Two-sided percentile interval used for the frozen outer bootstrap."""
    if not 0 < level < 1:
        raise ValueError("Interval level must be between zero and one")
    values = np.asarray(samples, dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("Percentile interval requires finite bootstrap samples")
    alpha = (1.0 - level) / 2.0
    return float(np.quantile(values, alpha)), float(np.quantile(values, 1.0 - alpha))


def _winner_at_last_endpoint(paths, horizon: int, gamma: float) -> str:
    candidates = candidate_return_matrix(paths)
    if len(candidates) < horizon:
        raise ValueError("Insufficient master OOS path before endpoint")
    scores = {name: ceq(candidates[name].iloc[-horizon:], gamma) for name in TIE_BREAK_ORDER}
    return min(TIE_BREAK_ORDER, key=lambda name: (-scores[name], TIE_BREAK_ORDER.index(name)))


def inner_winner_stability(
    returns_through_endpoint: pd.DataFrame,
    *,
    replications: int = 2000,
    seed: int = 20260909,
    lookback: int = 60,
    horizon: int = 120,
    transaction_cost: float = 0.0025,
    gamma: float = 5.0,
) -> dict[str, float | int | str]:
    """Compute endpoint-specific, full-procedure bootstrap winner stability.

    `returns_through_endpoint` must contain only information available at the
    endpoint. Its block length is intentionally re-estimated here, and this
    routine must never be called inside `outer_bootstrap`.
    """
    if replications < 1:
        raise ValueError("At least one inner replication is required")
    original_paths = run_headline_paths(returns_through_endpoint, lookback, transaction_cost)
    original_winner = _winner_at_last_endpoint(original_paths, horizon, gamma)
    block_length = protocol_block_length(returns_through_endpoint.to_numpy())
    rng = np.random.default_rng(seed)
    matching_winners = 0
    for _ in range(replications):
        pseudo_returns = stationary_resample(returns_through_endpoint, block_length, rng)
        pseudo_paths = run_headline_paths(pseudo_returns, lookback, transaction_cost)
        matching_winners += _winner_at_last_endpoint(pseudo_paths, horizon, gamma) == original_winner
    return {
        "endpoint": str(returns_through_endpoint.index[-1].date()),
        "winner": original_winner,
        "block_length": block_length,
        "replications": replications,
        "winner_stability": matching_winners / replications,
    }
