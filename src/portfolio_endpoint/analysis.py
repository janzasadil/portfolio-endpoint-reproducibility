"""Endpoint, survival, and ex-ante statistics from continuous portfolio paths."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .engine import PathResult

TIE_BREAK_ORDER = (
    "equal_weight",
    "sample_gmv",
    "ledoit_wolf_gmv",
    "inverse_volatility",
    "erc",
)


def ceq(returns: pd.Series | np.ndarray, gamma: float = 5.0) -> float:
    """Annualized net certainty-equivalent return under the frozen definition."""
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("CEQ requires at least two finite monthly returns")
    return float(12.0 * values.mean() - (gamma / 2.0) * 12.0 * values.var(ddof=1))


def candidate_return_matrix(paths: Mapping[str, PathResult]) -> pd.DataFrame:
    missing = set(TIE_BREAK_ORDER) - set(paths)
    if missing:
        raise ValueError(f"Missing headline paths: {sorted(missing)}")
    matrix = pd.concat({name: paths[name].net_returns for name in TIE_BREAK_ORDER}, axis=1)
    if matrix.isna().any().any() or not matrix.index.is_monotonic_increasing:
        raise ValueError("Candidate paths must be synchronized, complete, and ordered")
    return matrix


def _winner(scores: Mapping[str, float]) -> tuple[str, float, float]:
    ordered = sorted(TIE_BREAK_ORDER, key=lambda name: (-scores[name], TIE_BREAK_ORDER.index(name)))
    best, second = ordered[:2]
    return best, scores[best], scores[best] - scores[second]


def endpoint_reproducibility(
    paths: Mapping[str, PathResult],
    horizon: int = 120,
    displacement: int = 12,
    gamma: float = 5.0,
    december_only: bool = True,
) -> pd.DataFrame:
    """Compute the frozen endpoint-loss statistic at eligible origins.

    Each row is an earlier endpoint and its later displaced endpoint. Paths are
    only sliced; they are never rebuilt or re-formed at an endpoint.
    """
    returns = candidate_return_matrix(paths)
    if horizon < 2 or displacement < 1 or len(returns) < horizon + displacement:
        raise ValueError("Insufficient continuous OOS history for endpoint analysis")
    records: list[dict[str, object]] = []
    for earlier_pos in range(horizon - 1, len(returns) - displacement):
        earlier_date = returns.index[earlier_pos]
        if december_only and earlier_date.month != 12:
            continue
        later_pos = earlier_pos + displacement
        earlier_scores = {name: ceq(returns[name].iloc[earlier_pos - horizon + 1 : earlier_pos + 1], gamma)
                          for name in TIE_BREAK_ORDER}
        later_scores = {name: ceq(returns[name].iloc[later_pos - horizon + 1 : later_pos + 1], gamma)
                        for name in TIE_BREAK_ORDER}
        earlier_winner, _, earlier_margin = _winner(earlier_scores)
        later_winner, later_best, later_margin = _winner(later_scores)
        records.append({
            "earlier_endpoint": earlier_date,
            "later_endpoint": returns.index[later_pos],
            "earlier_winner": earlier_winner,
            "later_winner": later_winner,
            "earlier_margin": earlier_margin,
            "later_margin": later_margin,
            "endpoint_loss": later_best - later_scores[earlier_winner],
            "literal_switch": earlier_winner != later_winner,
            **{f"earlier_ceq_{name}": earlier_scores[name] for name in TIE_BREAK_ORDER},
            **{f"later_ceq_{name}": later_scores[name] for name in TIE_BREAK_ORDER},
        })
    return pd.DataFrame.from_records(records)


def endpoint_summary(endpoint_table: pd.DataFrame) -> dict[str, float]:
    loss = endpoint_table["endpoint_loss"]
    if loss.empty:
        raise ValueError("Endpoint table has no eligible origins")
    return {
        "mean_endpoint_loss": float(loss.mean()),
        "median_endpoint_loss": float(loss.median()),
        "p75_endpoint_loss": float(loss.quantile(0.75)),
        "p90_endpoint_loss": float(loss.quantile(0.90)),
        "literal_switch_frequency": float(endpoint_table["literal_switch"].mean()),
        "n_origins": int(len(endpoint_table)),
    }


def winner_survival(
    paths: Mapping[str, PathResult], horizon: int = 120, gamma: float = 5.0,
    december_only: bool = True,
) -> pd.DataFrame:
    """Annual-origin first-switch outcomes with monthly resolution and censoring."""
    returns = candidate_return_matrix(paths)
    winners: list[str] = []
    for end_pos in range(horizon - 1, len(returns)):
        scores = {name: ceq(returns[name].iloc[end_pos - horizon + 1 : end_pos + 1], gamma)
                  for name in TIE_BREAK_ORDER}
        winners.append(_winner(scores)[0])
    winner_index = returns.index[horizon - 1 :]
    records: list[dict[str, object]] = []
    for origin_pos, origin_date in enumerate(winner_index):
        if december_only and origin_date.month != 12:
            continue
        origin_winner = winners[origin_pos]
        future = next((step for step, winner in enumerate(winners[origin_pos + 1 :], start=1)
                       if winner != origin_winner), None)
        follow_up = len(winners) - origin_pos - 1
        records.append({
            "origin": origin_date,
            "winner": origin_winner,
            "time_months": future if future is not None else follow_up,
            "event": future is not None,
        })
    return pd.DataFrame.from_records(records)


def kaplan_meier(survival_table: pd.DataFrame) -> pd.DataFrame:
    """Product-limit curve; uncertainty is deliberately left to the outer bootstrap."""
    if survival_table.empty:
        raise ValueError("Survival table has no origins")
    records: list[dict[str, float]] = []
    probability = 1.0
    for time in sorted(survival_table["time_months"].unique()):
        at_risk = int((survival_table["time_months"] >= time).sum())
        events = int(((survival_table["time_months"] == time) & survival_table["event"]).sum())
        probability *= 1.0 - events / at_risk
        records.append({"time_months": int(time), "at_risk": at_risk, "events": events,
                        "survival": probability})
    return pd.DataFrame.from_records(records)


def ex_ante_selection(
    paths: Mapping[str, PathResult], horizon: int = 120, gamma: float = 5.0,
    december_only: bool = True,
) -> pd.DataFrame:
    """Past-window method choice evaluated over the following fixed future window."""
    returns = candidate_return_matrix(paths)
    if "ensemble" not in paths:
        raise ValueError("The separately traded ensemble path is required")
    ensemble = paths["ensemble"].net_returns.reindex(returns.index)
    records: list[dict[str, object]] = []
    for decision_pos in range(horizon - 1, len(returns) - horizon):
        decision_date = returns.index[decision_pos]
        if december_only and decision_date.month != 12:
            continue
        past = {name: ceq(returns[name].iloc[decision_pos - horizon + 1 : decision_pos + 1], gamma)
                for name in TIE_BREAK_ORDER}
        future = {name: ceq(returns[name].iloc[decision_pos + 1 : decision_pos + horizon + 1], gamma)
                  for name in TIE_BREAK_ORDER}
        selected, _, _ = _winner(past)
        oracle, oracle_ceq, _ = _winner(future)
        ensemble_ceq = ceq(ensemble.iloc[decision_pos + 1 : decision_pos + horizon + 1], gamma)
        records.append({
            "decision_date": decision_date,
            "selected_method": selected,
            "future_oracle": oracle,
            "selection_regret": oracle_ceq - future[selected],
            "selector_minus_ensemble": future[selected] - ensemble_ceq,
            "selector_hit": selected == oracle,
            **{f"past_ceq_{name}": past[name] for name in TIE_BREAK_ORDER},
            **{f"future_ceq_{name}": future[name] for name in TIE_BREAK_ORDER},
        })
    return pd.DataFrame.from_records(records)
