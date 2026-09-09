"""Continuous out-of-sample portfolio paths under the frozen timing protocol."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .methods import HEADLINE_METHODS


@dataclass(frozen=True)
class PathResult:
    weights: pd.DataFrame
    gross_returns: pd.Series
    net_returns: pd.Series
    turnover: pd.Series


def _drift(weights: np.ndarray, asset_returns: np.ndarray, gross_return: float) -> np.ndarray:
    denominator = 1.0 + gross_return
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("Portfolio gross return makes drifted holdings undefined")
    drifted = weights * (1.0 + asset_returns) / denominator
    if not np.isfinite(drifted).all():
        raise ValueError("Drifted holdings are nonfinite")
    return drifted


def run_continuous_path(
    returns: pd.DataFrame, target_rule, lookback: int, transaction_cost: float
) -> PathResult:
    """Run a target rule once, without endpoint-specific holding resets."""
    if lookback < 2 or len(returns) <= lookback:
        raise ValueError("Return matrix is too short for the requested lookback")
    if returns.isna().any().any() or not np.isfinite(returns.to_numpy()).all():
        raise ValueError("Return matrix contains missing or nonfinite values")

    values = returns.to_numpy(dtype=float)
    targets: list[np.ndarray] = []
    gross_returns: list[float] = []
    net_returns: list[float] = []
    turnovers: list[float] = []
    output_dates = returns.index[lookback:]
    previous_drifted: np.ndarray | None = None

    # At t=lookback-1, history ends at t and target is held over index lookback.
    for target_index in range(lookback - 1, len(returns) - 1):
        target = np.asarray(target_rule(values[target_index - lookback + 1 : target_index + 1]), dtype=float)
        held_returns = values[target_index + 1]
        gross = float(target @ held_returns)
        turnover = 0.0 if previous_drifted is None else 0.5 * float(np.abs(target - previous_drifted).sum())
        net = (1.0 - transaction_cost * turnover) * (1.0 + gross) - 1.0
        targets.append(target)
        gross_returns.append(gross)
        net_returns.append(net)
        turnovers.append(turnover)
        previous_drifted = _drift(target, held_returns, gross)

    return PathResult(
        weights=pd.DataFrame(targets, index=output_dates, columns=returns.columns),
        gross_returns=pd.Series(gross_returns, index=output_dates, name="gross_return"),
        net_returns=pd.Series(net_returns, index=output_dates, name="net_return"),
        turnover=pd.Series(turnovers, index=output_dates, name="turnover"),
    )


def run_headline_paths(returns: pd.DataFrame, lookback: int = 60, transaction_cost: float = 0.0025) -> dict[str, PathResult]:
    paths = {
        name: run_continuous_path(returns, rule, lookback, transaction_cost)
        for name, rule in HEADLINE_METHODS.items()
    }

    def ensemble_target(history: np.ndarray) -> np.ndarray:
        return np.mean([rule(history) for rule in HEADLINE_METHODS.values()], axis=0)

    paths["ensemble"] = run_continuous_path(returns, ensemble_target, lookback, transaction_cost)
    return paths
