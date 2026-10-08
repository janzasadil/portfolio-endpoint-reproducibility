import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint.analysis import TIE_BREAK_ORDER
from portfolio_endpoint.gap_perturbation import (
    decompose_pairs,
    durability_surface,
    monthly_panel_from_pairs,
    pairs_from_panel,
)


def pair_from_scores(earlier, later):
    # Independent first-maximum selection, not the implementation under test.
    initial_index = int(np.argmax(earlier))
    shifted_index = int(np.argmax(later))
    return pd.DataFrame(
        [
            {
                "earlier_endpoint": pd.Timestamp("2000-12-31"),
                "later_endpoint": pd.Timestamp("2001-12-31"),
                "earlier_winner": TIE_BREAK_ORDER[initial_index],
                "later_winner": TIE_BREAK_ORDER[shifted_index],
                "literal_switch": initial_index != shifted_index,
                "endpoint_loss": float(later[shifted_index] - later[initial_index]),
                **dict(zip((f"earlier_ceq_{m}" for m in TIE_BREAK_ORDER), earlier)),
                **dict(zip((f"later_ceq_{m}" for m in TIE_BREAK_ORDER), later)),
            }
        ]
    )


def test_random_score_changes_obey_both_identities():
    generator = np.random.default_rng(527)
    for _ in range(100):
        earlier = generator.normal(0, 0.1, len(TIE_BREAK_ORDER))
        later = earlier + generator.normal(0, 0.05, len(TIE_BREAK_ORDER))
        pairs = pair_from_scores(earlier, later)
        decomposition, audit = decompose_pairs(pairs, "synthetic", "test")
        initial_index = int(np.argmax(earlier))
        gap = earlier[initial_index] - earlier
        delta = (later - earlier) - (later[initial_index] - earlier[initial_index])
        np.testing.assert_allclose(decomposition.gap, gap, rtol=0, atol=1e-15)
        np.testing.assert_allclose(decomposition.relative_perturbation, delta, rtol=0, atol=1e-15)
        np.testing.assert_allclose(
            decomposition.excess_perturbation, later - later[initial_index], rtol=0, atol=1e-15
        )
        assert abs(audit.identity_residual.iloc[0]) < 1e-15
        assert audit.max_excess.iloc[0] == decomposition.excess_perturbation.max()


def test_exact_tie_can_change_reported_winner_with_zero_loss():
    earlier = np.array([0.0, 1.0, -1.0, -2.0, -3.0])
    later = np.array([0.5, 0.5, -1.0, -2.0, -3.0])
    # Shuffle column order to ensure the declared method order still governs.
    pairs = pair_from_scores(earlier, later).iloc[:, ::-1]
    decomposition, audit = decompose_pairs(pairs, "synthetic", "test")
    row = audit.iloc[0]
    assert row.initial_winner == "sample_gmv"
    assert row.shifted_window_reported_winner == "equal_weight"
    assert row.classification_mismatch and row.exact_top_tie
    assert row.endpoint_loss == 0
    assert row.mismatch_cause == "exact_shifted_top_tie"
    assert row.maximizing_competitor == "equal_weight"
    assert (
        decomposition.loc[decomposition.method == "sample_gmv", "excess_perturbation"].iloc[0] == 0
    )


def test_exact_initial_tie_keeps_first_method_in_frozen_order():
    pairs = pair_from_scores(np.zeros(5), np.zeros(5))
    _, audit = decompose_pairs(pairs, "synthetic", "test")
    assert audit.initial_winner.iloc[0] == "equal_weight"
    assert not audit.reported_winner_change.iloc[0]
    assert not audit.positive_endpoint_loss.iloc[0]
    assert audit.maximizing_competitor.iloc[0] == "equal_weight"


def test_near_tie_is_not_treated_as_exact_tie():
    earlier = np.array([0.0, -1.0, -2.0, -3.0, -4.0])
    later = np.array([0.0, 1e-14, -2.0, -3.0, -4.0])
    _, audit = decompose_pairs(pair_from_scores(earlier, later), "synthetic", "test")
    row = audit.iloc[0]
    assert row.shifted_window_reported_winner == "sample_gmv"
    assert row.apparent_top_tie and not row.exact_top_tie
    assert row.positive_endpoint_loss and not row.classification_mismatch
    assert row.endpoint_loss == 1e-14


def test_inconsistent_saved_winner_and_loss_are_rejected():
    pairs = pair_from_scores(np.zeros(5), np.arange(5, dtype=float))
    with pytest.raises(ValueError, match="tie rule"):
        decompose_pairs(pairs.assign(later_winner="equal_weight"), "synthetic", "test")
    with pytest.raises(ValueError, match="endpoint loss"):
        decompose_pairs(pairs.assign(endpoint_loss=100), "synthetic", "test")
    with pytest.raises(ValueError, match="finite"):
        decompose_pairs(pairs.assign(later_ceq_erc=np.nan), "synthetic", "test")


def test_surface_strict_threshold_and_no_reset_after_recovery():
    panel = pd.DataFrame(
        -1.0, index=pd.date_range("2000-12-31", periods=5, freq="ME"), columns=TIE_BREAK_ORDER
    )
    panel["equal_weight"] = 0.0
    panel.loc[panel.index[1], "sample_gmv"] = 0.0025
    panel.loc[panel.index[3], "sample_gmv"] = 0.005
    surface = durability_surface(panel, horizons=[1, 2, 3, 4], thresholds_bp=[0, 25, 50])

    def persistence(h, threshold):
        return surface.loc[
            (surface.h_months == h) & (surface.threshold_bp == threshold), "survival_fraction"
        ].iloc[0]

    assert persistence(1, 25) == 1  # Exactly 25 bp is not an exceedance.
    assert persistence(2, 0) == 0  # Recovery in month 2 does not undo month 1.
    assert persistence(3, 25) == 0
    assert persistence(4, 50) == 1
    assert (
        surface.groupby("h_months")
        .survival_fraction.apply(lambda s: s.is_monotonic_increasing)
        .all()
    )


def test_surface_counts_only_origins_with_horizon_followup():
    panel = pd.DataFrame(
        0.0, index=pd.date_range("2000-12-31", periods=26, freq="ME"), columns=TIE_BREAK_ORDER
    )
    surface = durability_surface(panel, horizons=[1, 2, 14, 26], thresholds_bp=[0])
    assert surface.n_origins.tolist() == [3, 2, 1, 0]
    assert surface.survival_fraction.iloc[:3].tolist() == [1, 1, 1]
    assert pd.isna(surface.survival_fraction.iloc[3])


def test_surface_zero_threshold_tracks_attainment_not_reported_identity():
    panel = pd.DataFrame(
        -1.0, index=pd.date_range("2000-12-31", periods=2, freq="ME"), columns=TIE_BREAK_ORDER
    )
    panel.iloc[0, 1] = 0.0
    panel.iloc[1, :2] = 0.0
    surface = durability_surface(panel, horizons=[1], thresholds_bp=[0])
    assert surface.survival_fraction.iloc[0] == 1


def test_panel_recovery_is_exact_and_rejects_conflicting_copies():
    panel = pd.DataFrame(
        np.arange(150, dtype=float).reshape(30, 5) / 1000,
        index=pd.date_range("2000-01-31", periods=30, freq="ME"),
        columns=TIE_BREAK_ORDER,
    )
    # Build all-month input pairs explicitly, so earlier/later coverage overlaps.
    rows = []
    for position in range(18):
        rows.append(
            {
                "earlier_endpoint": panel.index[position],
                "later_endpoint": panel.index[position + 12],
                **{f"earlier_ceq_{m}": panel.iloc[position][m] for m in TIE_BREAK_ORDER},
                **{f"later_ceq_{m}": panel.iloc[position + 12][m] for m in TIE_BREAK_ORDER},
            }
        )
    pairs = pd.DataFrame(rows)
    recovered = monthly_panel_from_pairs(pairs)
    pd.testing.assert_frame_equal(recovered, panel.rename_axis("endpoint"), check_freq=False)
    broken = pairs.copy()
    broken.loc[12, "earlier_ceq_equal_weight"] += 0.1
    with pytest.raises(ValueError, match="disagree"):
        monthly_panel_from_pairs(broken)
    displaced = pairs_from_panel(recovered, 6)
    assert displaced.earlier_endpoint.dt.month.eq(12).all()
    assert len(displaced) == 2


def test_surface_rejects_missing_months():
    panel = pd.DataFrame(
        0.0, index=pd.to_datetime(["2000-12-31", "2001-02-28"]), columns=TIE_BREAK_ORDER
    )
    with pytest.raises(ValueError, match="uninterrupted"):
        durability_surface(panel)
