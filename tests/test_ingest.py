import pytest

from portfolio_endpoint.ingest import parse_value_weighted_monthly


def test_parses_monthly_value_weighted_returns_as_decimals():
    text = """17 Industry Portfolios

Average Value Weighted Returns -- Monthly
,Food,Mines
192607,1.50,-2.00
192608,0.00,3.25

Average Equal Weighted Returns -- Monthly
"""
    panel = parse_value_weighted_monthly(text)
    assert list(panel.columns) == ["Food", "Mines"]
    assert panel.index[0].isoformat() == "1926-07-31T00:00:00"
    assert panel.loc["1926-08-31", "Mines"] == pytest.approx(0.0325)


def test_rejects_french_missing_codes():
    text = """Average Value Weighted Returns -- Monthly
,Food
192607,-99.99
"""
    with pytest.raises(ValueError, match="missing"):
        parse_value_weighted_monthly(text)


def test_rejects_a_missing_monthly_section():
    with pytest.raises(ValueError, match="not found"):
        parse_value_weighted_monthly("Some unrelated dataset\n")
