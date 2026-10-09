import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint.analysis import ceq
from portfolio_endpoint.change_return import change_return_categories
from portfolio_endpoint.ceq_component_decomposition import relative_components, reversal_points


@pytest.mark.parametrize(
    "changes,losses,expected",
    [
        ([False, False], [0, 0], ("A", "A25")),
        ([True, False], [0.003, 0], ("B", "B25")),
        ([False, True], [0, 0.003], ("C", "C25")),
        ([True, False], [0.0025, 0.0025], ("B", "A25")),
        ([True, True, False], [0.004, 0.001, 0], ("B", "B25")),
    ],
)
def test_change_and_return_uses_monthly_history_not_only_endpoint(changes, losses, expected):
    assert change_return_categories(changes, losses) == expected


def test_return_risk_components_exactly_reproduce_ceq_difference():
    initial = np.array([-0.01, 0.02, 0.003, 0.005])
    competitor = np.array([-0.02, 0.03, 0.004, 0.006])
    mean, risk = relative_components(initial, competitor)
    assert np.isclose(mean + risk, ceq(competitor) - ceq(initial), rtol=0, atol=1e-15)
    assert risk == -30 * (competitor.var(ddof=1) - initial.var(ddof=1))


def test_relative_change_decomposes_across_two_endpoints():
    initial0 = np.array([-0.01, 0.02, 0.003, 0.005])
    rival0 = np.array([-0.02, 0.03, 0.004, 0.006])
    initial1 = initial0 + 0.001
    rival1 = rival0 + 0.004
    mean0, risk0 = relative_components(initial0, rival0)
    mean1, risk1 = relative_components(initial1, rival1)
    relative = (ceq(rival1) - ceq(initial1)) - (ceq(rival0) - ceq(initial0))
    assert abs(relative - ((mean1 - mean0) + (risk1 - risk0))) < 1e-15


def test_invalid_return_cache_is_not_replaced_by_proxy():
    with pytest.raises(ValueError):
        relative_components([0, np.nan], [0, 0])


def test_gap_scatter_uses_shifted_winner_and_matches_vertical_loss():
    row = dict(
        earlier_endpoint="2000-12-31",
        later_endpoint="2001-12-31",
        earlier_winner="equal_weight",
        later_winner="sample_gmv",
        earlier_ceq_equal_weight=0.020,
        earlier_ceq_sample_gmv=0.018,
        later_ceq_equal_weight=0.017,
        later_ceq_sample_gmv=0.021,
        endpoint_loss=0.004,
        literal_switch=True,
    )
    points = reversal_points({"17_industries": (None, None, pd.DataFrame([row]))})
    point = points.iloc[0]
    assert np.isclose(point.initial_gap_bp, 20)
    assert np.isclose(point.relative_ceq_change_bp, 60)
    assert np.isclose(point.relative_ceq_change_bp - point.initial_gap_bp, point.endpoint_loss_bp)
    assert point.loss_gt25bp
