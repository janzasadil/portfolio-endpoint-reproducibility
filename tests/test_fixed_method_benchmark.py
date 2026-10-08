import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint.analysis import TIE_BREAK_ORDER
from portfolio_endpoint.fixed_method_benchmark import benchmark_selection, validate_headlines


def saved_selection(future_scores, selected_index=1):
    rows = []
    for year, future in enumerate(np.asarray(future_scores, dtype=float), start=2000):
        past = np.zeros(5)
        past[selected_index] = 1
        oracle_index = int(np.argmax(future))
        rows.append(
            {
                "decision_date": pd.Timestamp(year=year, month=12, day=31),
                "selected_method": TIE_BREAK_ORDER[selected_index],
                "future_oracle": TIE_BREAK_ORDER[oracle_index],
                "selector_hit": selected_index == oracle_index,
                "selection_regret": float(future[oracle_index] - future[selected_index]),
                **{f"past_ceq_{m}": past[i] for i, m in enumerate(TIE_BREAK_ORDER)},
                **{f"future_ceq_{m}": future[i] for i, m in enumerate(TIE_BREAK_ORDER)},
            }
        )
    return pd.DataFrame(rows)


def test_majority_and_minimum_regret_methods_need_not_coincide():
    scores = (
        np.array([[3, 2, 1, 0, -1], [3, 2, 1, 0, -1], [-100, 2, 1, 0, -1], [3, 2, 1, 0, -1]])
        / 10000
    )
    rates, regrets, summary, ties, decisions = benchmark_selection(saved_selection(scores), "test")
    assert rates.future_best_count.tolist() == [3, 1, 0, 0, 0]
    assert rates.future_best_share.sum() == 1
    assert summary["majority_method"] == "equal_weight"
    assert summary["best_fixed_method"] == "sample_gmv"
    assert not summary["majority_method_is_best_fixed_method"]
    assert summary["difference_pp"] == -50
    assert summary["best_fixed_mean_regret_bp"] == pytest.approx(0.75)
    assert summary["selector_minus_best_fixed_regret_bp"] == pytest.approx(0)
    gmv = regrets.loc[regrets.method == "sample_gmv"].iloc[0]
    assert gmv.median_regret_bp == pytest.approx(1)
    assert ties.empty
    assert (decisions.future_window_start > decisions.past_window_end).all()
    assert decisions.future_window_end.iloc[0] == pd.Timestamp("2010-12-31")


def test_exact_future_tie_uses_existing_order_and_is_disclosed():
    selection = saved_selection([[0.1, 0.1, 0, -1, -2]])
    rates, _, summary, ties, decisions = benchmark_selection(selection.iloc[:, ::-1], "test")
    assert rates.future_best_count.tolist() == [1, 0, 0, 0, 0]
    assert summary["future_best_tie_dates"] == 1
    assert summary["preceding_winner_hit_rate"] == 0
    assert summary["preceding_winner_mean_regret_bp"] == 0
    assert ties.reported_future_best_method.iloc[0] == "equal_weight"
    assert decisions.future_best_method.iloc[0] == "equal_weight"


def test_near_future_tie_is_not_reclassified_as_exact_tie():
    _, _, summary, ties, _ = benchmark_selection(saved_selection([[0, 1e-14, -1, -2, -3]]), "test")
    assert summary["preceding_winner_hit_rate"] == 1
    assert summary["majority_method"] == "sample_gmv"
    assert ties.empty


@pytest.mark.parametrize(
    "column,value,match",
    [
        ("future_oracle", "erc", "tie rule"),
        ("selected_method", "erc", "tie rule"),
        ("selection_regret", 99.0, "regret"),
        ("selector_hit", True, "hit"),
        ("future_ceq_equal_weight", np.nan, "finite"),
        ("decision_date", pd.Timestamp("2000-11-30"), "December"),
    ],
)
def test_invalid_saved_prospective_records_fail_loudly(column, value, match):
    selection = saved_selection([[2.0, 1.0, 0.0, -1.0, -2.0]])
    with pytest.raises(ValueError, match=match):
        benchmark_selection(selection.assign(**{column: value}), "test")


def test_benchmark_objective_ties_use_frozen_order_and_are_listed():
    selection = saved_selection([[1.0, 0.0, -1.0, -2.0, -3.0], [0.0, 1.0, -1.0, -2.0, -3.0]])
    _, _, summary, _, _ = benchmark_selection(selection, "test")
    assert summary["majority_method"] == "equal_weight"
    assert summary["best_fixed_method"] == "equal_weight"
    assert summary["tied_majority_methods"] == ["equal_weight", "sample_gmv"]
    assert summary["tied_best_fixed_methods"] == ["equal_weight", "sample_gmv"]


def test_headline_gate_checks_counts_rounding_and_exact_saved_values():
    summary = {
        "n_decisions": 75,
        "preceding_winner_hit_rate": 29 / 75,
        "preceding_winner_mean_regret_bp": 109.1158722878788,
    }
    saved = {"selector_hit_rate": 29 / 75, "mean_selection_regret": 109.1158722878788 / 10000}
    expected = ("unused", 75, "38.7", "109.12")
    validate_headlines(summary, saved, expected)
    with pytest.raises(ValueError, match="count"):
        validate_headlines({**summary, "n_decisions": 74}, saved, expected)
    with pytest.raises(ValueError, match="headline"):
        validate_headlines({**summary, "preceding_winner_mean_regret_bp": 109.2}, saved, expected)
    with pytest.raises(ValueError, match="frozen summary"):
        validate_headlines(summary, {**saved, "mean_selection_regret": 0.01}, expected)
