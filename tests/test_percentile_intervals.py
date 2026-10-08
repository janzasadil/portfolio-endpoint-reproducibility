import numpy as np
import pandas as pd

from portfolio_endpoint.qf_publication import saved_interval


def test_bootstrap_interval_uses_percentile_endpoints_not_normal_approximation(tmp_path):
    draws = pd.Series(np.arange(100, dtype=float))
    folder = tmp_path / "results/test_run"
    folder.mkdir(parents=True)
    draws.to_frame("metric").to_csv(folder / "outer_bootstrap.csv", index=False)
    low, high = saved_interval(tmp_path, "test_run", "metric")
    assert (low, high) == tuple(np.percentile(draws, [2.5, 97.5]))


def test_bootstrap_interval_accepts_non_normal_draws(tmp_path):
    draws = pd.Series([0.0] * 95 + [100.0] * 5)
    folder = tmp_path / "results/test_run"
    folder.mkdir(parents=True)
    draws.to_frame("metric").to_csv(folder / "outer_bootstrap.csv", index=False)
    low, high = saved_interval(tmp_path, "test_run", "metric")
    assert low == 0.0
    assert high > 0.0
