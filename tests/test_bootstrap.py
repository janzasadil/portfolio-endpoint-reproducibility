import numpy as np

from portfolio_endpoint.bootstrap import corrected_pw_stationary_block_length, protocol_block_length, stationary_indices


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
