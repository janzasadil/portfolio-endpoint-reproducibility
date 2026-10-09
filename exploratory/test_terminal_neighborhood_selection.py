import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint.analysis import TIE_BREAK_ORDER, _winner
from exploratory.terminal_neighborhood_selection import (
    historical_neighborhood,
    minimax_selection,
)


def test_j0_reproduces_current_winner_including_ties():
    for values in ([1, 2, 3, 4, 5], [1, 3, 3, 2, 0], [0, 0, 0, 0, 0]):
        expected = _winner(dict(zip(TIE_BREAK_ORDER, values)))[0]
        assert minimax_selection([values])[0] == expected


def test_method_that_never_wins_can_be_minimax_optimal():
    values = np.array([[10, 0, 8, -1, -1], [0, 10, 8, -1, -1]])
    selected, worst, ties = minimax_selection(values)
    assert (values.argmax(axis=1) != 2).all()
    assert selected == TIE_BREAK_ORDER[2]
    assert worst[2] == 2
    assert ties == (TIE_BREAK_ORDER[2],)


def test_exact_minimax_ties_resolve_in_frozen_order():
    selected, _, ties = minimax_selection([[10, 0, 0, 0, 0], [0, 10, 0, 0, 0]])
    assert ties == TIE_BREAK_ORDER  # Every method has worst shortfall 10.
    assert selected == TIE_BREAK_ORDER[0]


def test_historical_neighborhood_has_no_lookahead_and_includes_both_endpoints():
    panel = pd.DataFrame(
        np.arange(30).reshape(6, 5),
        index=pd.period_range("2000-01", periods=6, freq="M"),
        columns=TIE_BREAK_ORDER,
    )
    original = historical_neighborhood(panel, "2000-04-30", 2)
    np.testing.assert_array_equal(original, panel.iloc[1:4].to_numpy())
    panel.loc["2000-05":] = 1e12
    np.testing.assert_array_equal(historical_neighborhood(panel, "2000-04-30", 2), original)


def test_missing_month_is_not_silently_accepted():
    panel = pd.DataFrame(
        np.zeros((3, 5)),
        index=pd.PeriodIndex(["2000-01", "2000-03", "2000-04"], freq="M"),
        columns=TIE_BREAK_ORDER,
    )
    with pytest.raises(ValueError, match="Incomplete"):
        historical_neighborhood(panel, "2000-04-30", 2)
