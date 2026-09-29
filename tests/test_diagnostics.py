import pandas as pd
import pytest

from portfolio_endpoint.diagnostics import (
    audit_summary,
    selector_fixed_method_summary,
    survival_audit_from_winners,
)


def _panel(winners):
    dates = pd.date_range("2000-12-31", periods=len(winners), freq="ME")
    return pd.DataFrame({"winner": winners, "best_ceq": [0.1] * len(winners)}, index=dates)


def test_first_switch_is_not_reversed_by_recovery():
    audit = survival_audit_from_winners(_panel(["a", "a", "b", "a", "a"]), december_only=False)
    first = audit.iloc[0]
    assert first.event and first.survival_duration_months == 2
    assert first.first_failure_date == pd.Timestamp("2001-02-28")
    assert first.winner_at_12 is pd.NA  # no complete twelve-month follow-up


def test_administrative_censoring_and_complete_followup_eligibility():
    panel = _panel(["a"] * 14)
    audit = survival_audit_from_winners(panel, december_only=False)
    assert not audit.iloc[0].event and audit.iloc[0].censored
    summary = audit_summary(audit)
    assert summary["n_complete_12"] == 2
    assert summary["survival_12_complete_followup"] == pytest.approx(1.0)


def test_material_failure_uses_fixed_original_winner():
    panel = _panel(["a", "a", "a"])
    panel["a"], panel["b"] = [.1, .09, .1], [.1, .1, .1]
    for method in ("equal_weight", "sample_gmv", "ledoit_wolf_gmv", "inverse_volatility", "erc"):
        panel[method] = panel["a"]
    panel["equal_weight"] = panel["a"]
    audit = survival_audit_from_winners(panel, december_only=False, material_threshold=.005)
    assert audit.iloc[0].event and audit.iloc[0].survival_duration_months == 1


def test_selector_fixed_comparisons_are_paired_and_report_all_methods():
    methods = ("equal_weight", "sample_gmv", "ledoit_wolf_gmv", "inverse_volatility", "erc")
    rows = []
    for selected, oracle, values in [
        ("equal_weight", "equal_weight", [.03, .01, .0, .0, .0]),
        ("sample_gmv", "erc", [.00, .01, .0, .0, .02]),
    ]:
        row = {"selected_method": selected, "future_oracle": oracle}
        row.update({f"future_ceq_{method}": value for method, value in zip(methods, values)})
        rows.append(row)
    result = selector_fixed_method_summary(pd.DataFrame(rows)).set_index("fixed_method")
    assert set(result.index) == set(methods)
    assert result.loc["equal_weight", "mean_selector_minus_fixed"] == pytest.approx(.005)
    assert result.loc["erc", "future_candidate_winner_frequency"] == pytest.approx(.5)
