import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint.engine import run_continuous_path


def test_path_applies_drift_turnover_and_cost_without_initial_entry_cost():
    returns = pd.DataFrame(
        {"a": [0.0, 0.0, 0.10, 0.0], "b": [0.0, 0.0, 0.0, 0.0]},
        index=pd.date_range("2000-01-31", periods=4, freq="ME"),
    )
    path = run_continuous_path(returns, lambda history: np.array([0.5, 0.5]), 2, 0.01)
    assert path.turnover.iloc[0] == 0.0
    assert path.net_returns.iloc[0] == pytest.approx(path.gross_returns.iloc[0])  # cost-free formation
    # After a 5% portfolio gain, the first asset drifts to 0.5 * 1.1 / 1.05.
    assert path.turnover.iloc[1] == pytest.approx(0.0238095238)


def test_path_starts_after_lookback_and_has_one_weight_vector_per_held_month():
    returns = pd.DataFrame(np.zeros((5, 2)), index=pd.date_range("2000-01-31", periods=5, freq="ME"))
    path = run_continuous_path(returns, lambda history: np.array([0.5, 0.5]), 2, 0.0)
    assert len(path.net_returns) == 3
    assert path.weights.index.equals(path.net_returns.index)


def test_quarterly_rebalance_does_not_trade_between_scheduled_dates():
    returns = pd.DataFrame(np.full((8, 2), [0.02, 0.0]), index=pd.date_range("2000-01-31", periods=8, freq="ME"))
    path = run_continuous_path(returns, lambda history: np.array([0.5, 0.5]), 2, 0.01, rebalance_every=3)
    assert path.turnover.iloc[1] == 0.0
    assert path.turnover.iloc[2] == 0.0
