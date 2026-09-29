import numpy as np
import pandas as pd

from portfolio_endpoint.reporting import bootstrap_interval


def test_bootstrap_interval_uses_percentile_endpoints_not_normal_approximation():
    draws = pd.Series(np.arange(100, dtype=float))
    low, high = bootstrap_interval(draws)
    assert (low, high) == tuple(np.percentile(draws, [2.5, 97.5]))


def test_bootstrap_interval_accepts_non_normal_draws():
    draws = pd.Series([0.0] * 95 + [100.0] * 5)
    low, high = bootstrap_interval(draws)
    assert low == 0.0
    assert high > 0.0
