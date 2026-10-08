import pandas as pd

from portfolio_endpoint.design_sensitivity import summarize


def test_materiality_is_strict_and_rates_are_from_counts_not_rounded_losses():
    table = pd.DataFrame({
        "endpoint_loss": [0, 25 / 10000, 25.000001 / 10000],
        "literal_switch": [False, True, True],
        "earlier_endpoint": pd.to_datetime(["2000-12-31", "2001-12-31", "2002-12-31"]),
    })
    result = summarize(table)
    assert result["switch_count"] == 2
    assert result["loss_gt25_count"] == 1
    assert result["loss_gt25_rate_pct"] == 100 / 3
    assert result["switch_rate_pct"] == 200 / 3
    assert result["median_loss_ceq_bp"] == 25
