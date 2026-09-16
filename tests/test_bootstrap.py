import numpy as np
import pytest

import pandas as pd

from portfolio_endpoint.bootstrap import (
    corrected_pw_stationary_block_length,
    percentile_interval,
    protocol_block_length,
    stationary_indices,
    stationary_resample,
    circular_block_indices,
)


def test_stationary_indices_are_circular_and_reproducible():
    indices = stationary_indices(7, 3, np.random.default_rng(2026))
    assert len(indices) == 7
    assert ((indices >= 0) & (indices < 7)).all()
    assert np.array_equal(indices, stationary_indices(7, 3, np.random.default_rng(2026)))


def test_protocol_block_length_is_bounded_and_uses_both_dependence_proxies():
    rng = np.random.default_rng(7)
    returns = rng.normal(size=(144, 4))
    block_length = protocol_block_length(returns)
    assert 2 <= block_length <= 12
    assert 2 <= corrected_pw_stationary_block_length(returns.mean(axis=1)) <= 12


def test_resample_preserves_calendar_and_percentile_interval_is_two_sided():
    frame = pd.DataFrame({"a": range(12), "b": range(12, 24)}, index=pd.date_range("2000-01-31", periods=12, freq="ME"))
    sampled = stationary_resample(frame, 3, np.random.default_rng(1))
    assert sampled.index.equals(frame.index)
    assert percentile_interval(np.array([0, 1, 2, 3, 4]), level=0.8) == pytest.approx((0.4, 3.6))


def test_replication_seed_streams_are_stable_across_chunk_boundaries():
    first_chunk = [stationary_indices(20, 3, np.random.default_rng(np.random.SeedSequence([99, i]))) for i in range(3)]
    resumed = stationary_indices(20, 3, np.random.default_rng(np.random.SeedSequence([99, 2])))
    assert np.array_equal(first_chunk[2], resumed)


def test_circular_block_indices_have_fixed_contiguous_blocks():
    indices = circular_block_indices(10, 3, np.random.default_rng(2))
    assert len(indices) == 10
    assert ((indices >= 0) & (indices < 10)).all()
