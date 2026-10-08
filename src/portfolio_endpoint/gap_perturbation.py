"""Exploratory gap/perturbation and durability diagnostics from saved CEQs only.

No portfolio construction, resampling, or new CEQ estimation is performed.
Exact reported winners use the existing tie rule; numerical tolerances are
validation diagnostics, never a replacement for that rule.
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER, _winner
from .ingest import project_root

IDENTITY_ATOL = 1e-12
APPARENT_TIE_ATOL = 1e-12
BASELINE_RUNS = {
    "17_industries": "primary_17_definitive_B2000",
    "14_countries": "country_replication_B1000",
    "30_industries": "replication_30_B1000",
}
LABELS = {
    "17_industries": "17 U.S. industries",
    "14_countries": "14 developed-country markets",
    "30_industries": "30 U.S. industries",
}
FULL_SAMPLE = "december_full_eligible"
COMMON_SAMPLE = "december_common_origins_h6_h12_h24"


def read_pairs(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        parse_dates=["earlier_endpoint", "later_endpoint"],
        float_precision="round_trip",
    )


def validate_panel(panel: pd.DataFrame) -> None:
    """Require an uninterrupted finite monthly panel in frozen method order."""
    if not isinstance(panel.index, pd.DatetimeIndex) or panel.empty:
        raise ValueError("CEQ panel requires a nonempty datetime index")
    periods = panel.index.to_period("M")
    if not periods.equals(pd.period_range(periods[0], periods[-1], freq="M")):
        raise ValueError("CEQ panel must have one uninterrupted row per month")
    if not np.isfinite(panel.loc[:, list(TIE_BREAK_ORDER)].to_numpy()).all():
        raise ValueError("CEQ panel contains nonfinite scores")


def monthly_panel_from_pairs(pairs: pd.DataFrame) -> pd.DataFrame:
    """Recover persisted monthly scores by merging earlier and later endpoints.

    Overlapping copies must agree exactly. No return windows are re-evaluated.
    """
    frames = []
    for prefix in ("earlier", "later"):
        frame = pairs[[f"{prefix}_ceq_{m}" for m in TIE_BREAK_ORDER]].copy()
        frame.columns = list(TIE_BREAK_ORDER)
        frame.index = pd.DatetimeIndex(pairs[f"{prefix}_endpoint"], name="endpoint")
        frames.append(frame)
    merged = pd.concat(frames).sort_index()
    for _, copies in merged.loc[merged.index.duplicated(keep=False)].groupby(level=0):
        if not (copies.to_numpy() == copies.iloc[0].to_numpy()).all():
            raise ValueError("Persisted copies of a monthly CEQ disagree")
    panel = merged.loc[~merged.index.duplicated()].copy()
    validate_panel(panel)
    return panel


def pairs_from_panel(panel: pd.DataFrame, displacement: int) -> pd.DataFrame:
    """Construct December pairs using saved CEQs, not newly computed returns."""
    validate_panel(panel)
    if displacement < 1:
        raise ValueError("Displacement must be positive")
    records = []
    for position in range(len(panel) - displacement):
        if panel.index[position].month != 12:
            continue
        earlier = panel.iloc[position].to_dict()
        later = panel.iloc[position + displacement].to_dict()
        initial, _, initial_margin = _winner(earlier)
        shifted, best, shifted_margin = _winner(later)
        records.append(
            {
                "earlier_endpoint": panel.index[position],
                "later_endpoint": panel.index[position + displacement],
                "earlier_winner": initial,
                "later_winner": shifted,
                "earlier_margin": initial_margin,
                "later_margin": shifted_margin,
                "endpoint_loss": best - later[initial],
                "literal_switch": initial != shifted,
                **{f"earlier_ceq_{m}": earlier[m] for m in TIE_BREAK_ORDER},
                **{f"later_ceq_{m}": later[m] for m in TIE_BREAK_ORDER},
            }
        )
    return pd.DataFrame.from_records(records)


def decompose_pairs(
    pairs: pd.DataFrame,
    universe: str,
    sample: str,
    horizon: int = 120,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return a five-method long decomposition and one audit row per pair."""
    decompositions, audits = [], []
    for _, row in pairs.iterrows():
        earlier = {m: float(row[f"earlier_ceq_{m}"]) for m in TIE_BREAK_ORDER}
        later = {m: float(row[f"later_ceq_{m}"]) for m in TIE_BREAK_ORDER}
        if not np.isfinite([*earlier.values(), *later.values()]).all():
            raise ValueError("Endpoint CEQs must be finite")
        initial = _winner(earlier)[0]
        shifted, shifted_best, _ = _winner(later)
        if initial != row.earlier_winner or shifted != row.later_winner:
            raise ValueError("Saved winner conflicts with the exact frozen tie rule")
        reported_change = initial != shifted
        if reported_change != bool(row.literal_switch):
            raise ValueError("Saved literal-switch indicator conflicts with winners")
        loss = float(row.endpoint_loss)
        direct_loss = shifted_best - later[initial]
        if loss < 0 or abs(loss - direct_loss) > IDENTITY_ATOL:
            raise ValueError("Saved endpoint loss conflicts with the shifted CEQs")
        gaps = {m: earlier[initial] - earlier[m] for m in TIE_BREAK_ORDER}
        perturbations = {
            m: (later[m] - earlier[m]) - (later[initial] - earlier[initial])
            for m in TIE_BREAK_ORDER
        }
        excesses = {m: perturbations[m] - gaps[m] for m in TIE_BREAK_ORDER}
        competitor, maximum, _ = _winner(excesses)
        identity_residual = loss - maximum
        if abs(identity_residual) > IDENTITY_ATOL:
            raise ValueError("Gap/perturbation identity fails")
        term_residuals = {m: excesses[m] - (later[m] - later[initial]) for m in TIE_BREAK_ORDER}
        if max(map(abs, term_residuals.values())) > IDENTITY_ATOL:
            raise ValueError("Method-level gap/perturbation identity fails")
        start, end = pd.Timestamp(row.earlier_endpoint), pd.Timestamp(row.later_endpoint)
        displacement = end.to_period("M").ordinal - start.to_period("M").ordinal
        if displacement < 1:
            raise ValueError("Endpoint pairs must be forward displaced")
        common = {
            "universe": universe,
            "sample": sample,
            "horizon_months": horizon,
            "terminal_date": start,
            "displaced_terminal_date": end,
            "displacement_months": displacement,
            "initial_winner": initial,
            "shifted_window_reported_winner": shifted,
            "endpoint_loss": loss,
            "reported_winner_change": reported_change,
            "positive_endpoint_loss": loss > 0,
            "classification_mismatch": reported_change != (loss > 0),
            "max_excess": maximum,
            "identity_residual": identity_residual,
            "max_method_identity_residual": max(map(abs, term_residuals.values())),
            "maximizing_competitor": competitor,
            "maximizing_competitor_differs_from_reported_winner": competitor != shifted,
            "competitor_gap": gaps[competitor],
            "competitor_perturbation": perturbations[competitor],
            "competitor_excess": excesses[competitor],
        }
        for method in TIE_BREAK_ORDER:
            decompositions.append(
                {
                    **common,
                    "method": method,
                    "is_maximizing_competitor": method == competitor,
                    "initial_ceq": earlier[method],
                    "shifted_ceq": later[method],
                    "gap": gaps[method],
                    "relative_perturbation": perturbations[method],
                    "excess_perturbation": excesses[method],
                    "direct_shifted_advantage": later[method] - later[initial],
                    "method_identity_residual": term_residuals[method],
                }
            )
        separations = [abs(later[a] - later[b]) for a, b in combinations(TIE_BREAK_ORDER, 2)]
        initial_separations = [
            abs(earlier[a] - earlier[b]) for a, b in combinations(TIE_BREAK_ORDER, 2)
        ]
        initial_top = [m for m in TIE_BREAK_ORDER if earlier[m] == earlier[initial]]
        apparent_initial_top = [
            m for m in TIE_BREAK_ORDER if earlier[initial] - earlier[m] <= APPARENT_TIE_ATOL
        ]
        apparent_ties = [
            {
                "endpoint": prefix,
                "method_a": a,
                "method_b": b,
                "ceq_a": scores[a],
                "ceq_b": scores[b],
                "absolute_separation": abs(scores[a] - scores[b]),
            }
            for prefix, scores in (("initial", earlier), ("shifted", later))
            for a, b in combinations(TIE_BREAK_ORDER, 2)
            if abs(scores[a] - scores[b]) <= APPARENT_TIE_ATOL
        ]
        top = [m for m in TIE_BREAK_ORDER if later[m] == shifted_best]
        near_top = [m for m in TIE_BREAK_ORDER if shifted_best - later[m] <= APPARENT_TIE_ATOL]
        runner_up_gap = (
            sorted(later.values(), reverse=True)[0] - sorted(later.values(), reverse=True)[1]
        )
        audits.append(
            {
                **common,
                "exact_top_tie": len(top) > 1,
                "apparent_top_tie": len(near_top) > 1,
                "exact_initial_top_tie": len(initial_top) > 1,
                "apparent_initial_top_tie": len(apparent_initial_top) > 1,
                "exact_initial_top_methods": json.dumps(initial_top),
                "apparent_initial_top_methods": json.dumps(apparent_initial_top),
                "apparent_candidate_ties": json.dumps(apparent_ties),
                "apparent_candidate_tie_count": len(apparent_ties),
                "min_absolute_ceq_separation_either_endpoint": min(
                    *separations, *initial_separations
                ),
                "min_apparent_tie_separation": min(
                    (t["absolute_separation"] for t in apparent_ties), default=np.nan
                ),
                "exact_top_methods": json.dumps(top),
                "apparent_top_methods": json.dumps(near_top),
                "initial_attains_shifted_maximum": later[initial] == shifted_best,
                "positive_direct_ceq_shortfall": direct_loss > 0,
                "stored_positive_loss_matches_direct_shortfall": (loss > 0) == (direct_loss > 0),
                "min_absolute_shifted_ceq_separation": min(separations),
                "min_positive_shifted_ceq_separation": min(
                    (v for v in separations if v > 0), default=np.nan
                ),
                "shifted_top_two_ceq_separation": runner_up_gap,
                "mismatch_cause": (
                    "exact_shifted_top_tie"
                    if reported_change and loss == 0 and initial in top
                    else (
                        "numerical_saved_loss_discrepancy"
                        if reported_change != (loss > 0)
                        else "none"
                    )
                ),
                **{f"initial_ceq_{m}": earlier[m] for m in TIE_BREAK_ORDER},
                **{f"shifted_ceq_{m}": later[m] for m in TIE_BREAK_ORDER},
            }
        )
    return pd.DataFrame(decompositions), pd.DataFrame(audits)


def summarize_decomposition(audits: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["universe", "sample", "horizon_months", "displacement_months"]
    for key, group in audits.groupby(keys, sort=False):
        strata = {
            "all_pairs": group,
            "reported_winner_change": group.loc[group.reported_winner_change],
            "endpoint_loss_gt25bp": group.loc[group.endpoint_loss > 0.0025],
        }
        for name, selected in strata.items():
            record = {
                **dict(zip(keys, key)),
                "stratum": name,
                "n_pairs": len(selected),
                "reported_winner_changes": int(selected.reported_winner_change.sum()),
                "positive_endpoint_losses": int(selected.positive_endpoint_loss.sum()),
                "classification_mismatches": int(selected.classification_mismatch.sum()),
                "exact_top_ties": int(selected.exact_top_tie.sum()),
                "apparent_top_ties": int(selected.apparent_top_tie.sum()),
                "exact_initial_top_ties": int(selected.exact_initial_top_tie.sum()),
                "apparent_initial_top_ties": int(selected.apparent_initial_top_tie.sum()),
                "min_absolute_ceq_separation_either_endpoint": selected.min_absolute_ceq_separation_either_endpoint.min(),
                "min_apparent_tie_separation": selected.min_apparent_tie_separation.min(),
                "max_abs_identity_residual": selected.identity_residual.abs().max(),
                "min_absolute_shifted_ceq_separation": selected.min_absolute_shifted_ceq_separation.min(),
                "min_positive_shifted_ceq_separation": selected.min_positive_shifted_ceq_separation.min(),
                "min_shifted_top_two_ceq_separation": selected.shifted_top_two_ceq_separation.min(),
            }
            for quantity in ("gap", "perturbation", "excess"):
                values = selected[f"competitor_{quantity}"] * 10000
                for statistic, value in (
                    ("mean", values.mean()),
                    ("median", values.median()),
                    ("p75", values.quantile(0.75)),
                    ("p90", values.quantile(0.9)),
                ):
                    record[f"competitor_{quantity}_{statistic}_bp"] = value
            rows.append(record)
    return pd.DataFrame(rows)


def durability_surface(
    panel: pd.DataFrame,
    horizons=range(1, 121),
    thresholds_bp=range(101),
) -> pd.DataFrame:
    """Direct complete-follow-up persistence, not Kaplan--Meier survival.

    December origin winners are fixed once. An exceedance at any intervening
    month is permanent failure, even after recovery. Eligibility depends on h;
    therefore curves across h can reflect cohort changes, not just attrition.
    A zero threshold means continued maximizer attainment, not reported identity.
    """
    validate_panel(panel)
    horizons = list(horizons)
    thresholds_bp = np.asarray(list(thresholds_bp), dtype=float)
    if not horizons or any(h < 1 or int(h) != h for h in horizons):
        raise ValueError("Horizons must be positive integer months")
    if not len(thresholds_bp) or not np.isfinite(thresholds_bp).all() or (thresholds_bp < 0).any():
        raise ValueError("Thresholds must be finite and nonnegative")
    values = panel.loc[:, list(TIE_BREAK_ORDER)].to_numpy()
    best = values.max(axis=1)
    origin_paths = []
    for position in np.flatnonzero(panel.index.month == 12):
        original = _winner(panel.iloc[position].to_dict())[0]
        method_position = TIE_BREAK_ORDER.index(original)
        losses = best[position + 1 :] - values[position + 1 :, method_position]
        origin_paths.append(np.maximum.accumulate(losses))
    records = []
    for horizon in horizons:
        maxima = np.asarray([path[horizon - 1] for path in origin_paths if len(path) >= horizon])
        n = len(maxima)
        # Compare native units, so the existing strict threshold is preserved.
        counts = (maxima[:, None] <= thresholds_bp[None, :] / 10000).sum(axis=0)
        for threshold, count in zip(thresholds_bp, counts):
            records.append(
                {
                    "h_months": horizon,
                    "threshold_bp": threshold,
                    "n_origins": n,
                    "n_surviving": int(count),
                    "survival_fraction": float(count / n) if n else np.nan,
                    "estimator": "direct_complete_followup_proportion",
                }
            )
    return pd.DataFrame(records)


def save_heatmap(surface: pd.DataFrame, title: str, path: Path) -> None:
    grid = surface.pivot(index="threshold_bp", columns="h_months", values="survival_fraction")
    fig, ax = plt.subplots(figsize=(7.4, 4.7), constrained_layout=True)
    image = ax.imshow(
        grid.to_numpy() * 100,
        origin="lower",
        aspect="auto",
        cmap="viridis",
        vmin=0,
        vmax=100,
        extent=(0.5, 120.5, -0.5, 100.5),
        interpolation="nearest",
    )
    ax.set(
        title=title,
        xlabel="Months since initial terminal date",
        ylabel="Tolerance threshold (annualized CEQ bp)",
        xticks=[1, 12, 24, 60, 120],
    )
    for threshold in (25, 50):
        ax.axhline(threshold, color="white", linestyle="--", linewidth=0.7, alpha=0.65)
    fig.colorbar(image, ax=ax, label="Persistence: complete-follow-up origins (%)")
    fig.savefig(path, dpi=240)
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def validate_saved_slices(root: Path, surfaces: dict[str, pd.DataFrame]) -> pd.DataFrame:
    saved = pd.read_csv(
        root / "results/extension/materiality_threshold_sensitivity.csv",
        float_precision="round_trip",
    )
    checks = []
    for universe, saved_name in (("17_industries", "primary17"), ("14_countries", "countries")):
        for threshold in (0, 25, 50):
            existing = saved.loc[
                (saved.universe == saved_name) & (saved.threshold_bp == threshold)
            ].iloc[0]
            for horizon in (12, 24):
                actual = (
                    surfaces[universe]
                    .loc[
                        (surfaces[universe].h_months == horizon)
                        & (surfaces[universe].threshold_bp == threshold)
                    ]
                    .iloc[0]
                )
                probability = float(existing[f"survival_{horizon}_complete_followup"])
                n = int(existing[f"n_complete_{horizon}"])
                residual = actual.survival_fraction - probability
                if actual.n_origins != n or abs(residual) > IDENTITY_ATOL:
                    raise ValueError(
                        "Surface does not reproduce existing complete-follow-up slices"
                    )
                checks.append(
                    {
                        "universe": universe,
                        "h_months": horizon,
                        "threshold_bp": threshold,
                        "n_origins": n,
                        "saved_survival_fraction": probability,
                        "surface_survival_fraction": actual.survival_fraction,
                        "residual": residual,
                    }
                )
    return pd.DataFrame(checks)


def diagnostic_report(audits, summary, surfaces, provenance) -> str:
    baseline = summary.loc[
        (summary["sample"] == FULL_SAMPLE)
        & (summary.horizon_months == 120)
        & (summary.displacement_months == 12)
    ]
    residual = audits.identity_residual.abs().max()
    lines = [
        "# Gap-perturbation and durability diagnostic",
        "",
        "Descriptive exploratory accounting only; no inference or manuscript changes.",
        "",
        "## Identity and tie audit",
        "",
        f"The identity passed for all {len(audits):,} pair/cohort records (including explicitly labeled "
        f"common-origin copies). Maximum absolute residual: {residual:.17g} native annualized CEQ "
        f"({10000 * residual:.17g} bp). Method-level maximum residual: "
        f"{audits.max_method_identity_residual.max():.17g}. Validation tolerance is {IDENTITY_ATOL:g}; "
        "it never changes winner selection, positive-loss classification, or threshold comparisons.",
        "",
        "| Baseline universe (H=120, h=12) | Pairs | Reported changes | Positive losses | Mismatches |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in baseline.loc[baseline.stratum == "all_pairs"].itertuples():
        lines.append(
            f"| {LABELS[row.universe]} | {row.n_pairs} | {row.reported_winner_changes} | "
            f"{row.positive_endpoint_losses} | {row.classification_mismatches} |"
        )
    mismatches = audits.loc[audits.classification_mismatch]
    zero_changes = int((audits.reported_winner_change & ~audits.positive_endpoint_loss).sum())
    lines += [
        "",
        f"Across all covered cohorts: {len(mismatches)} classification mismatches; "
        f"{zero_changes} reported changes with zero stored loss. Every mismatch, its cause, "
        "all initial/shifted CEQs, and exact/apparent top-tie methods are in `winner_change_tie_audit.csv`.",
        "",
        f"Exact shifted top ties: {int(audits.exact_top_tie.sum())}; apparent shifted top ties "
        f"within {APPARENT_TIE_ATOL:g} CEQ: {int(audits.apparent_top_tie.sum())}. "
        f"Minimum absolute shifted separation among any two candidate CEQs: "
        f"{audits.min_absolute_shifted_ceq_separation.min():.17g}; minimum strictly positive separation: "
        f"{audits.min_positive_shifted_ceq_separation.min():.17g}. Minimum best/runner-up separation: "
        f"{audits.shifted_top_two_ceq_separation.min():.17g}. These are native CEQ units, not bp.",
        "",
    ]
    apparent = audits.loc[audits.apparent_top_tie]
    lines.append(
        "Minimum best/runner-up separation around an apparent top tie: "
        + (
            f"{apparent.shifted_top_two_ceq_separation.min():.17g}."
            if len(apparent)
            else "not applicable: no apparent top ties at the stated tolerance."
        )
    )
    lines += [
        "",
        f"Initial endpoint exact/apparent top ties: "
        f"{int(audits.exact_initial_top_tie.sum())}/{int(audits.apparent_initial_top_tie.sum())}. "
        f"Minimum absolute separation across either endpoint: "
        f"{audits.min_absolute_ceq_separation_either_endpoint.min():.17g}. "
        f"Candidate-pair apparent ties (including below the top): "
        f"{int(audits.apparent_candidate_tie_count.sum())}. "
        "Their methods, CEQs, and separations are in `apparent_ceq_tie_audit.csv`.",
        f"Stored positive loss agrees with direct shifted-window nonattainment of the maximum "
        f"for every record: {bool(audits.stored_positive_loss_matches_direct_shortfall.all())}.",
    ]
    lines += [
        "",
        (
            "Winner ties do not affect the covered empirical classifications."
            if not len(mismatches) and not audits.exact_top_tie.any()
            else "Do not equate reported winner changes with positive economic loss; consult the tie audit."
        ),
        "",
        "## Gap and relative perturbation pattern",
        "",
        "The competitor is the maximizer of the computed delta-minus-gap vector under the frozen "
        "method ordering. The initial winner is included: on unchanged-winner observations it usually "
        "maximizes with gap=delta=excess=0. All-pair summaries therefore contain structural zeros. "
        "The decomposition is an exact accounting identity, not a causal explanation.",
        "",
        "| Universe | Conditioning | n | Mean gap (bp) | Mean relative perturbation (bp) | Mean excess (bp) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in baseline.itertuples():
        lines.append(
            f"| {LABELS[row.universe]} | {row.stratum} | {row.n_pairs} | "
            f"{row.competitor_gap_mean_bp:.2f} | {row.competitor_perturbation_mean_bp:.2f} | "
            f"{row.competitor_excess_mean_bp:.2f} |"
        )
    lines += [
        "",
        "Median, p75, and p90 for each quantity and every separately labeled cohort are in "
        "`gap_perturbation_summary.csv`. Phase samples, H=60 checks, full eligible samples, and "
        "common-origin copies must not be pooled as independent observations.",
        "",
    ]
    for universe in BASELINE_RUNS:
        changed = baseline.loc[
            (baseline.universe == universe) & (baseline.stratum == "reported_winner_change")
        ].iloc[0]
        material = baseline.loc[
            (baseline.universe == universe) & (baseline.stratum == "endpoint_loss_gt25bp")
        ].iloc[0]
        lines.append(
            f"{LABELS[universe]}: among reported switches the median initial competitor gap is "
            f"{changed.competitor_gap_median_bp:.2f} bp, median relative perturbation "
            f"{changed.competitor_perturbation_median_bp:.2f} bp, and median excess "
            f"{changed.competitor_excess_median_bp:.2f} bp. In the >25-bp subset, the mean initial "
            f"gap is {material.competitor_gap_mean_bp:.2f} bp versus "
            f"{changed.competitor_gap_mean_bp:.2f} bp among all switches. These descriptively larger "
            "gaps require correspondingly larger relative perturbations; material failures are not "
            "simply the smallest initial races. Sparse conditional groups warrant caution."
        )
    lines += [
        "",
        "## Durability surface",
        "",
        "Direct proportions use December origins with at least h observed future months. For each "
        "origin the initial winner is held fixed; losses are calculated from saved monthly CEQs and "
        "accumulated with a running maximum over months 1 through h. A first loss strictly greater "
        "than tau is permanent failure, even after recovery. Grid: h=1..120, tau=0..100 CEQ bp in "
        "1-bp steps. No Kaplan--Meier censoring adjustment is used. Denominators N_h change with h; "
        "horizon profiles need not be monotone because cohorts change. For fixed h they must be "
        "nondecreasing in tau. Tau=0 measures continued attainment of the CEQ maximum, not necessarily "
        "unchanged reported identity in a tie.",
        "",
        "All twelve 0/25/50-bp slices at h=12/24 reproduce the existing complete-follow-up estimates "
        "and eligible counts. They are not mislabeled as the existing full-sample KM estimates.",
        "",
        "| Universe | h | N_h | S(h,0) | S(h,25) | S(h,50) | S(h,100) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for universe, surface in surfaces.items():
        for horizon in (12, 24, 60, 120):
            selected = surface.loc[surface.h_months == horizon].set_index("threshold_bp")
            probabilities = [
                f"{100 * selected.loc[t, 'survival_fraction']:.1f}%" for t in (0, 25, 50, 100)
            ]
            lines.append(
                f"| {LABELS[universe]} | {horizon} | {int(selected.n_origins.iloc[0])} | "
                + " | ".join(probabilities)
                + " |"
            )
    for universe, surface in surfaces.items():
        at_120 = surface.loc[surface.h_months == 120].set_index("threshold_bp")
        increase = 100 * (
            at_120.loc[100, "survival_fraction"] - at_120.loc[50, "survival_fraction"]
        )
        lines += [
            "",
            f"At h=120, increasing tolerance from 50 to 100 bp raises persistence by "
            f"{increase:.1f} percentage points for {LABELS[universe]}. This quantifies the "
            "extra threshold detail beyond the existing 0/25/50-bp slices.",
        ]
    lines += [
        "",
        "The surface exposes intermediate tolerance thresholds and horizons, but the rows above "
        "largely extend the already reported literal/material persistence contrast. It is a useful "
        "inspection artifact, not a new estimand or inferential result. A changing-cohort heatmap "
        "is less direct for the paper than its existing 0/25/50-bp survival presentation.",
        "",
        "## Recommendation",
        "",
        "**Decomposition only.** Use the gap/perturbation accounting as a "
        "compact descriptive diagnostic; keep the full durability surface in the reproducibility "
        "package. It adds threshold detail but is substantially redundant with existing persistence "
        "results and uses a different complete-follow-up population from the KM curves. No automatic "
        "manuscript insertion is recommended.",
        "",
        "## Reused versus recomputed",
        "",
    ]
    lines += [f"- {item}" for item in provenance["operations"]]
    lines += [
        "",
        "30-industry coverage is the saved baseline H=120/h=12 CEQ pairs only. Its monthly CEQs "
        "and h=6/24 CEQ pairs were not persisted here, so no paths were rebuilt to extend that scope.",
        "",
        "Input paths, grids, tolerance, and exact coverage are recorded in `diagnostic_manifest.json`.",
    ]
    return "\n".join(lines) + "\n"


def run(root: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(
            "Use a new diagnostic directory; existing outputs are not overwritten"
        )
    sources, decomposition_parts, audit_parts, panels = [], [], [], {}

    def add(pairs, universe, sample, horizon=120):
        decomposition, audit = decompose_pairs(pairs, universe, sample, horizon)
        decomposition_parts.append(decomposition)
        audit_parts.append(audit)

    baseline = {}
    for universe, folder in BASELINE_RUNS.items():
        path = root / "results" / folder / "endpoint_pairs.csv"
        sources.append(str(path.relative_to(root)))
        baseline[universe] = read_pairs(path)
        add(baseline[universe], universe, FULL_SAMPLE)
    for universe in ("17_industries", "14_countries"):
        for horizon in (120, 60):
            path = (
                root
                / "results/calendar_window_robustness"
                / f"{universe}_H{horizon}_monthly_endpoint_pairs.csv"
            )
            sources.append(str(path.relative_to(root)))
            pairs = read_pairs(path)
            if horizon == 120:
                panels[universe] = monthly_panel_from_pairs(pairs)
                restored = pairs_from_panel(panels[universe], 12)
                pd.testing.assert_frame_equal(restored, baseline[universe], check_exact=True)
            for month, group in pairs.groupby(pairs.earlier_endpoint.dt.month):
                if horizon == 120 and month == 12:
                    continue  # Already included from the canonical baseline.
                sample = FULL_SAMPLE if month == 12 else f"annual_phase_{month:02d}_full_eligible"
                add(group, universe, sample, horizon)
        horizon_pairs = {h: pairs_from_panel(panels[universe], h) for h in (6, 12, 24)}
        common = set.intersection(*(set(p.earlier_endpoint) for p in horizon_pairs.values()))
        profile_path = (
            root
            / "results/extension"
            / (
                "primary17_displacement.csv"
                if universe == "17_industries"
                else "countries_displacement.csv"
            )
        )
        profile = pd.read_csv(profile_path, float_precision="round_trip")
        sources.append(str(profile_path.relative_to(root)))
        for displacement, pairs in horizon_pairs.items():
            if displacement != 12:
                add(pairs, universe, FULL_SAMPLE)
            matched = pairs.loc[pairs.earlier_endpoint.isin(common)]
            add(matched, universe, COMMON_SAMPLE)
            for label, selected in (("full_eligible", pairs), ("common_calendar_origins", matched)):
                saved = profile.loc[
                    (profile.h == displacement) & (profile["sample"] == label)
                ].iloc[0]
                if (
                    len(selected) != saved.n_origins
                    or abs(selected.endpoint_loss.mean() - saved.mean_endpoint_loss) > IDENTITY_ATOL
                ):
                    raise ValueError("Reused CEQs do not reproduce the saved displacement profile")
    decomposition = pd.concat(decomposition_parts, ignore_index=True)
    audits = pd.concat(audit_parts, ignore_index=True)
    summary = summarize_decomposition(audits)
    surfaces = {universe: durability_surface(panel) for universe, panel in panels.items()}
    checks = validate_saved_slices(root, surfaces)
    sources.append("results/extension/materiality_threshold_sensitivity.csv")
    provenance = {
        "input_files": sources,
        "tie_break_order": list(TIE_BREAK_ORDER),
        "identity_atol": IDENTITY_ATOL,
        "apparent_tie_atol": APPARENT_TIE_ATOL,
        "horizons_months": [1, 120],
        "thresholds_bp": [0, 100],
        "threshold_step_bp": 1,
        "pair_cohort_records": len(audits),
        "method_records": len(decomposition),
        "coverage": summary.loc[
            summary.stratum == "all_pairs",
            [
                "universe",
                "sample",
                "horizon_months",
                "displacement_months",
                "n_pairs",
            ],
        ].to_dict(orient="records"),
        "max_absolute_identity_residual": float(audits.identity_residual.abs().max()),
        "operations": [
            "Reused canonical baseline endpoint-pair CEQs, losses, and winners for all three universes.",
            "Reused existing H=120/H=60 monthly endpoint-pair CEQs for all twelve annual calendar phases of the primary and country universes.",
            "Recovered complete H=120 monthly CEQ panels by merging persisted earlier/later scores; overlapping copies agree exactly.",
            "Reconstructed h=6/24 December pairs by looking up saved monthly CEQs; validated the existing full/common-origin profiles.",
            "Computed algebraic gaps, relative perturbations, residuals, tie audits, and descriptive summaries from those saved CEQs.",
            "Computed running maxima and complete-follow-up surface proportions from those same monthly CEQs; checked existing 0/25/50-bp slices.",
            "No CEQs, portfolio paths, bootstrap replications, manuscript files, or publication outputs were recomputed or modified.",
        ],
        "recommendation": "decomposition only",
    }
    output.mkdir(parents=True)
    decomposition.to_csv(output / "gap_perturbation_decomposition.csv", index=False)
    summary.to_csv(output / "gap_perturbation_summary.csv", index=False)
    audits.loc[audits.classification_mismatch].to_csv(
        output / "winner_change_tie_audit.csv", index=False
    )
    audits.loc[audits.apparent_candidate_tie_count > 0].to_csv(
        output / "apparent_ceq_tie_audit.csv", index=False
    )
    audits.to_csv(output / "winner_change_audit_all_pairs.csv", index=False)
    checks.to_csv(output / "durability_slice_validation.csv", index=False)
    for universe, suffix in (("17_industries", "us"), ("14_countries", "intl")):
        surfaces[universe].to_csv(output / f"durability_surface_{suffix}.csv", index=False)
        save_heatmap(
            surfaces[universe], LABELS[universe], output / f"durability_heatmap_{suffix}.png"
        )
    (output / "diagnostic_manifest.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )
    (output / "GAP_PERTURBATION_REPORT.md").write_text(
        diagnostic_report(audits, summary, surfaces, provenance),
        encoding="utf-8",
    )
    print(f"Finished: {output}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = project_root()
    run(root, args.output_dir or root / "results/gap_perturbation_diagnostic")


if __name__ == "__main__":
    main()
