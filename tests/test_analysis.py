import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint.analysis import ceq, endpoint_reproducibility, endpoint_summary, kaplan_meier, survival_summary
from portfolio_endpoint.engine import PathResult


def _path(values: list[float], dates: pd.DatetimeIndex) -> PathResult:
    series = pd.Series(values, index=dates)
    return PathResult(pd.DataFrame({"asset": [1.0] * len(dates)}, index=dates), series, series, series * 0)


def test_ceq_uses_monthly_sample_variance_and_annualization():
    values = np.array([0.01, 0.03])
    assert ceq(values, gamma=5) == pytest.approx(12 * 0.02 - 2.5 * 12 * 0.0002)


def test_endpoint_loss_uses_the_earlier_winner_on_later_window():
    dates = pd.date_range("2000-01-31", periods=8, freq="ME")
    paths = {
        "equal_weight": _path([.04, .04, .04, 0, 0, 0, 0, 0], dates),
        "sample_gmv": _path([0, 0, 0, .10, .10, .10, .10, .10], dates),
        "ledoit_wolf_gmv": _path([0] * 8, dates),
        "inverse_volatility": _path([0] * 8, dates),
        "erc": _path([0] * 8, dates),
    }
    table = endpoint_reproducibility(paths, horizon=3, displacement=2, gamma=0, december_only=False)
    first = table.iloc[0]
    assert first.earlier_winner == "equal_weight"
    assert first.endpoint_loss > 0
    assert endpoint_summary(table)["n_origins"] == len(table)


def test_kaplan_meier_handles_censoring_without_iid_standard_errors():
    table = pd.DataFrame({"time_months": [1, 2, 2], "event": [True, False, True]})
    curve = kaplan_meier(table)
    assert curve.survival.tolist() == pytest.approx([2 / 3, 1 / 3])
    assert survival_summary(curve)["survival_12_months"] == pytest.approx(1 / 3)
