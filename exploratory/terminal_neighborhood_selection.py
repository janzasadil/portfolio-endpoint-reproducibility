"""Prespecified minimax terminal-neighborhood selector from frozen CEQs only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from portfolio_endpoint.analysis import TIE_BREAK_ORDER, _winner
from portfolio_endpoint.fixed_method_benchmark import benchmark_selection

SAMPLES = {
    "17_industries": "primary_17_definitive_B2000",
    "14_countries": "country_replication_B1000",
}
HORIZON = 120
PRIMARY_J = 12
SENSITIVITY_J = (6, 24)


def historical_neighborhood(panel: pd.DataFrame, decision_date, neighborhood: int):
    """Exactly d-J,...,d; neither future rows nor partial neighborhoods are allowed."""
    if neighborhood < 0 or int(neighborhood) != neighborhood:
        raise ValueError("J must be a nonnegative integer")
    decision = pd.Timestamp(decision_date).to_period("M")
    months = pd.period_range(decision - neighborhood, decision, freq="M")
    if not months.isin(panel.index).all():
        raise ValueError("Incomplete historical endpoint neighborhood")
    scores = panel.loc[months, list(TIE_BREAK_ORDER)].to_numpy(dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError("Historical CEQs must be finite")
    return scores


def minimax_selection(scores):
    """Choose smallest worst shortfall, resolving exact ties in frozen method order."""
    values = np.asarray(scores, dtype=float)
    if (
        values.ndim != 2
        or values.shape[1] != len(TIE_BREAK_ORDER)
        or not len(values)
        or not np.isfinite(values).all()
    ):
        raise ValueError("Expected finite historical CEQs in the five-method frozen order")
    worst = (values.max(axis=1, keepdims=True) - values).max(axis=0)
    tied = np.flatnonzero(worst == worst.min())
    return TIE_BREAK_ORDER[int(tied[0])], worst, tuple(TIE_BREAK_ORDER[int(i)] for i in tied)


def saved_monthly_panel(path):
    """Merge persisted endpoint CEQs without estimating any return-window statistic."""
    pairs = pd.read_csv(path, float_precision="round_trip")
    pieces = []
    for prefix in ("earlier", "later"):
        frame = pairs[[f"{prefix}_ceq_{m}" for m in TIE_BREAK_ORDER]].copy()
        frame.columns = list(TIE_BREAK_ORDER)
        frame.index = pd.to_datetime(pairs[f"{prefix}_endpoint"]).dt.to_period("M")
        pieces.append(frame)
    merged = pd.concat(pieces).sort_index()
    for _, group in merged.loc[merged.index.duplicated(keep=False)].groupby(level=0):
        if not (group.to_numpy() == group.iloc[0].to_numpy()).all():
            raise ValueError("Overlapping persisted CEQs disagree")
    panel = merged.loc[~merged.index.duplicated()]
    if not panel.index.equals(pd.period_range(panel.index[0], panel.index[-1], freq="M")):
        raise ValueError("Saved monthly CEQ panel has gaps")
    if not np.isfinite(panel.to_numpy()).all():
        raise ValueError("Saved monthly CEQs contain undefined values")
    return panel


def validate_inputs(root):
    inputs, checks = {}, []
    for universe, folder in SAMPLES.items():
        selected = pd.read_csv(
            root / f"results/{folder}/ex_ante_selection.csv", float_precision="round_trip"
        )
        # Existing saved-only validator verifies all labels, published means/hits,
        # finite scores, annual dates, exact tie rule, and per-decision regret.
        benchmark_selection(selected, universe)
        panel = saved_monthly_panel(
            root / f"results/calendar_window_robustness/{universe}_H120_monthly_endpoint_pairs.csv"
        )
        for _, row in selected.iterrows():
            decision = pd.Timestamp(row.decision_date).to_period("M")
            past = np.array([row[f"past_ceq_{m}"] for m in TIE_BREAK_ORDER])
            future = np.array([row[f"future_ceq_{m}"] for m in TIE_BREAK_ORDER])
            if not np.array_equal(
                historical_neighborhood(panel, decision.to_timestamp("M"), 0)[0], past
            ):
                raise ValueError("Historical CEQs at d disagree with the frozen selector")
            if not np.array_equal(panel.loc[decision + HORIZON].to_numpy(), future):
                raise ValueError(
                    "Following 120-month CEQs do not match the saved ending-month scores"
                )
            if minimax_selection(past[None, :])[0] != row.selected_method:
                raise ValueError("J=0 fails to reproduce the frozen selector")
        checks.append(
            dict(
                universe=universe,
                n_original=len(selected),
                first_decision=selected.decision_date.iloc[0],
                last_decision=selected.decision_date.iloc[-1],
                historical_panel_start=str(panel.index[0]),
                historical_panel_end=str(panel.index[-1]),
                current_mean_regret_bp=float(selected.selection_regret.mean() * 10000),
                current_hit_rate=float(selected.selector_hit.mean()),
                current_mean_selector_minus_ensemble_bp=float(
                    selected.selector_minus_ensemble.mean() * 10000
                ),
                j0_reproduces_every_original_decision=True,
                historical_and_future_ceq_arrays_match_saved_monthly_scores_exactly=True,
            )
        )
        inputs[universe] = (panel, selected)
    return inputs, checks


def evaluate_selector(panel, original, universe, neighborhood):
    records = []
    for _, row in original.iterrows():
        decision = pd.Timestamp(row.decision_date).to_period("M")
        months = pd.period_range(decision - neighborhood, decision, freq="M")
        if not months.isin(panel.index).all():
            continue  # Eligibility excludes this date for BOTH selectors.
        historical = historical_neighborhood(panel, decision.to_timestamp("M"), neighborhood)
        method, worst, ties = minimax_selection(historical)
        current = row.selected_method
        if minimax_selection(historical[-1:])[0] != current:
            raise ValueError("J=0 disagrees on a common eligible decision")
        future = {m: float(row[f"future_ceq_{m}"]) for m in TIE_BREAK_ORDER}
        oracle, best, _ = _winner(future)
        current_regret = best - future[current]
        stable_regret = best - future[method]
        if min(current_regret, stable_regret) < 0:
            raise ValueError("Negative regret")
        if abs(current_regret - row.selection_regret) > 1e-12:
            raise ValueError("Current decision-level regret does not reproduce")
        # Same saved, separately traded ensemble CEQ; no pooled-return metric.
        ensemble = future[current] - row.selector_minus_ensemble
        records.append(
            dict(
                universe=universe,
                j_months=neighborhood,
                decision_date=str(decision.to_timestamp("M").date()),
                historical_first_endpoint=str(months[0]),
                historical_last_endpoint=str(months[-1]),
                earliest_historical_window_start=str(months[0] - (HORIZON - 1)),
                future_window_start=str(decision + 1),
                future_window_end=str(decision + HORIZON),
                current_method=current,
                stable_method=method,
                future_best_method=oracle,
                current_regret_bp=current_regret * 10000,
                stable_regret_bp=stable_regret * 10000,
                delta_regret_bp=(stable_regret - current_regret) * 10000,
                current_hit=current == oracle,
                stable_hit=method == oracle,
                method_changed=method != current,
                stable_lower_regret=stable_regret < current_regret,
                current_selector_minus_ensemble_bp=float(row.selector_minus_ensemble * 10000),
                stable_selector_minus_ensemble_bp=float((future[method] - ensemble) * 10000),
                selected_minimax_shortfall_bp=float(worst[TIE_BREAK_ORDER.index(method)] * 10000),
                minimax_tie_count=len(ties),
                minimax_tied_methods="|".join(ties),
                future_top_tie_count=sum(v == best for v in future.values()),
                **{
                    f"minimax_shortfall_bp_{m}": float(worst[i] * 10000)
                    for i, m in enumerate(TIE_BREAK_ORDER)
                },
                **{f"future_ceq_bp_{m}": future[m] * 10000 for m in TIE_BREAK_ORDER},
            )
        )
    if not records:
        raise ValueError("No common eligible decisions")
    return pd.DataFrame(records)


def summarize(decisions, original_count):
    first = decisions.iloc[0]
    result = dict(
        universe=first.universe,
        j_months=int(first.j_months),
        n_common=len(decisions),
        n_original=original_count,
        n_excluded=original_count - len(decisions),
        first_decision=decisions.decision_date.iloc[0],
        last_decision=decisions.decision_date.iloc[-1],
        paired_mean_delta_regret_bp=float(decisions.delta_regret_bp.mean()),
        paired_median_delta_regret_bp=float(decisions.delta_regret_bp.median()),
        lower_regret_fraction=float(decisions.stable_lower_regret.mean()),
        higher_regret_fraction=float((decisions.delta_regret_bp > 0).mean()),
        equal_regret_fraction=float((decisions.delta_regret_bp == 0).mean()),
        method_changed_fraction=float(decisions.method_changed.mean()),
        exact_minimax_tied_decisions=int((decisions.minimax_tie_count > 1).sum()),
        exact_future_top_tied_decisions=int((decisions.future_top_tie_count > 1).sum()),
    )
    for selector in ("current", "stable"):
        regret = decisions[f"{selector}_regret_bp"]
        for name, value in dict(
            mean=regret.mean(),
            median=regret.median(),
            p75=regret.quantile(0.75),
            p90=regret.quantile(0.9),
            maximum=regret.max(),
        ).items():
            result[f"{selector}_{name}_regret_bp"] = float(value)
        result[f"{selector}_hit_rate"] = float(decisions[f"{selector}_hit"].mean())
        result[f"{selector}_mean_selector_minus_ensemble_bp"] = float(
            decisions[f"{selector}_selector_minus_ensemble_bp"].mean()
        )
        for method in TIE_BREAK_ORDER:
            count = int((decisions[f"{selector}_method"] == method).sum())
            result[f"{selector}_count_{method}"] = count
            result[f"{selector}_share_{method}"] = count / len(decisions)
    shortfall = decisions.selected_minimax_shortfall_bp
    for name, value in dict(
        minimum=shortfall.min(),
        mean=shortfall.mean(),
        median=shortfall.median(),
        p75=shortfall.quantile(0.75),
        p90=shortfall.quantile(0.9),
        maximum=shortfall.max(),
    ).items():
        result[f"selected_minimax_{name}_bp"] = float(value)
    delta = decisions.delta_regret_bp
    result["largest_positive_delta_bp"] = float(delta.max())
    result["paired_mean_delta_excluding_largest_positive_bp"] = float(
        delta.drop(delta.idxmax()).mean()
    )
    return result


def write_report(output, summary, checks):
    lines = [
        "# Terminal-date-neighborhood selector: prespecified exploratory comparison",
        "",
        "H=120; primary J=12; sensitivity J=6/24. Monthly neighborhoods include J+1 endpoints d-J,...,d. All CEQs are frozen saved values; no portfolios, return-window CEQs, bootstrap draws, or manuscript files were reconstructed or changed.",
        "",
        "## Current published selector validation",
        "",
        "| Universe | Original decisions | Hit rate | Mean regret (CEQ bp) | Mean selector minus ensemble (CEQ bp) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for c in checks:
        lines.append(
            f"| {c['universe']} | {c['n_original']} | {100*c['current_hit_rate']:.2f}% | {c['current_mean_regret_bp']:.2f} | {c['current_mean_selector_minus_ensemble_bp']:.2f} |"
        )
    lines += [
        "",
        "These full-sample published values are validation only. All subsequent current-versus-stable comparisons use the SAME eligible decisions within each universe and J; J-specific samples are not silently interchanged.",
        "",
        "## Primary J=12 comparison",
        "",
        "| Universe | Common n | Current mean regret | Stable mean regret | Paired mean delta | Paired median delta | Lower regret | Current hit | Stable hit | Current p90 | Stable p90 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in summary.loc[summary.j_months == PRIMARY_J].iterrows():
        lines.append(
            f"| {r.universe} | {r.n_common} | {r.current_mean_regret_bp:.2f} | {r.stable_mean_regret_bp:.2f} | {r.paired_mean_delta_regret_bp:+.2f} | {r.paired_median_delta_regret_bp:+.2f} | {100*r.lower_regret_fraction:.2f}% | {100*r.current_hit_rate:.2f}% | {100*r.stable_hit_rate:.2f}% | {r.current_p90_regret_bp:.2f} | {r.stable_p90_regret_bp:.2f} |"
        )
    lines += [
        "",
        "Regret quantities and signed differences are annualized CEQ bp; negative paired differences favor the stable selector.",
        "",
        "## All prespecified neighborhoods",
        "",
        "| Universe | J | Common n | Current mean | Stable mean | Paired mean delta | Different method | Current hit | Stable hit |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r.universe} | {r.j_months} | {r.n_common} | {r.current_mean_regret_bp:.2f} | {r.stable_mean_regret_bp:.2f} | {r.paired_mean_delta_regret_bp:+.2f} | {100*r.method_changed_fraction:.2f}% | {100*r.current_hit_rate:.2f}% | {100*r.stable_hit_rate:.2f}% |"
        )
    lines += [
        "",
        "## Full regret and ensemble summaries",
        "",
        "| Universe | J | Selector | Median | p75 | p90 | Maximum | Mean selector minus ensemble |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in summary.iterrows():
        for selector in ("current", "stable"):
            vals = [
                r[f"{selector}_{metric}_regret_bp"]
                for metric in ("median", "p75", "p90", "maximum")
            ]
            lines.append(
                f"| {r.universe} | {r.j_months} | {selector} | "
                + " | ".join(f"{v:.2f}" for v in vals)
                + f" | {r[f'{selector}_mean_selector_minus_ensemble_bp']:.2f} |"
            )
    lines += [
        "",
        "## Selected minimax shortfall distribution",
        "",
        "| Universe | J | Minimum | Mean | Median | p75 | p90 | Maximum | Exact tied decisions |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in summary.iterrows():
        vals = [
            r[f"selected_minimax_{metric}_bp"]
            for metric in ("minimum", "mean", "median", "p75", "p90", "maximum")
        ]
        lines.append(
            f"| {r.universe} | {r.j_months} | "
            + " | ".join(f"{v:.2f}" for v in vals)
            + f" | {r.exact_minimax_tied_decisions} |"
        )
    lines += [
        "",
        "## Method-selection frequencies",
        "",
        "Cells are count (share); current and stable are compared on common dates.",
        "",
        "| Universe | J | Selector | Equal weight | Sample GMV | Ledoit-Wolf GMV | Inverse volatility | ERC |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in summary.iterrows():
        for selector in ("current", "stable"):
            cells = [
                f"{r[f'{selector}_count_{m}']} ({100*r[f'{selector}_share_{m}']:.1f}%)"
                for m in TIE_BREAK_ORDER
            ]
            lines.append(
                f"| {r.universe} | {r.j_months} | {selector} | " + " | ".join(cells) + " |"
            )
    lines += [
        "",
        "## Validation, timing, costs and uncertainty",
        "",
        "J=0 reproduces the current method at every original and every common eligible decision. All historical inputs end no later than d. A historical score at month t describes t-119,...,t; following evaluation is d+1,...,d+120, and its saved CEQs match the monthly panel at d+120 exactly. Historical/future windows at a decision do not overlap, but following windows at adjacent annual decisions overlap by 108 months. Eligibility excludes dates without all J+1 historical endpoints, not dates with poor performance.",
        "",
        "Tie resolution is exact (no approximate tie tolerance): equal_weight, sample_gmv, ledoit_wolf_gmv, inverse_volatility, erc. Minimax ties and future-best top ties are disclosed in the summary CSV; the decision CSV lists all tied minimax methods. Regrets are nonnegative and conversions use 10,000 bp per native annualized CEQ unit.",
        "",
        "Both selected methods inherit their preconstructed continuous method-specific return streams and within-method transaction costs. The ensemble retains its own separately traded stream; its saved decision-level CEQ is recovered algebraically from current CEQ minus the saved signed difference. No extra cross-method transition trade is charged. These results are method-selection comparisons, not an executable switching strategy; interpreting them as such would require a separate holdings/transition-cost analysis.",
        "",
        "No uncertainty interval is supplied. Saved asset-level bootstrap summaries cannot evaluate this new selector; the heavily overlapping prospective windows invalidate a simple IID decision bootstrap. An appropriate paired dependence-aware procedure would require additional prespecification/implementation; none was added. No statistical-significance claim is made.",
        "",
        "## Primary interpretation and recommendation",
        "",
    ]
    for _, r in summary.loc[summary.j_months == PRIMARY_J].iterrows():
        lines.append(
            f"For {r.universe}, mean regret changes by {r.paired_mean_delta_regret_bp:+.2f} bp, p90 by {r.stable_p90_regret_bp-r.current_p90_regret_bp:+.2f} bp, and maximum regret by {r.stable_maximum_regret_bp-r.current_maximum_regret_bp:+.2f} bp. Excluding the decision with the largest unfavorable paired change leaves a mean difference of {r.paired_mean_delta_excluding_largest_positive_bp:+.2f} bp; this is an influence diagnostic, not an alternative primary estimate. The stable method has lower/higher/equal regret in {100*r.lower_regret_fraction:.2f}%/{100*r.higher_regret_fraction:.2f}%/{100*r.equal_regret_fraction:.2f}% of decisions."
        )
        lines.append("")
    lines += [
        "Classification: **Unhelpful**. The primary J=12 selector increases average regret in both universes and does not deliver a coherent prospective improvement. All three prespecified J values have worse mean regret; a sensitivity-specific hit-rate improvement does not justify selecting J after the fact. Upper-tail changes must be read alongside these adverse averages, not reframed as a successful selector. Recommendation: **discard it as a paper addition**, while preserving this negative exploratory result as a reproducibility artifact; no claim of broader novelty is made.",
        "",
        "## Provenance",
        "",
        "Historical inputs: results/calendar_window_robustness/{17_industries,14_countries}_H120_monthly_endpoint_pairs.csv (persisted earlier/later scores merged, overlapping copies required to agree exactly). Future/current inputs: results/{primary_17_definitive_B2000,country_replication_B1000}/ex_ante_selection.csv. Original CEQ/window/tie definitions: analysis.ceq, analysis._winner, analysis.ex_ante_selection. Primary J=12 outputs are saved in primary_J12_frozen.json before the J=6/24 artifact evaluations. No unrelated analyses or publication changes were run.",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def run(root):
    inputs, checks = validate_inputs(root)
    output = root / "results/terminal_neighborhood_selection"
    output.mkdir(parents=True, exist_ok=True)
    parts, summaries = [], []
    for universe, (panel, original) in inputs.items():
        decisions = evaluate_selector(panel, original, universe, PRIMARY_J)
        parts.append(decisions)
        summaries.append(summarize(decisions, len(original)))
    (output / "primary_J12_frozen.json").write_text(
        json.dumps(
            {
                "primary_j": PRIMARY_J,
                "horizon": HORIZON,
                "sensitivity_j": SENSITIVITY_J,
                "tie_order": TIE_BREAK_ORDER,
                "baseline_validation": checks,
                "primary_results": summaries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    for neighborhood in SENSITIVITY_J:
        for universe, (panel, original) in inputs.items():
            decisions = evaluate_selector(panel, original, universe, neighborhood)
            parts.append(decisions)
            summaries.append(summarize(decisions, len(original)))
    decisions = pd.concat(parts, ignore_index=True)
    summary = pd.DataFrame(summaries).sort_values(["universe", "j_months"])
    decisions.to_csv(output / "decisions.csv", index=False)
    summary.to_csv(output / "summary.csv", index=False)
    write_report(output, summary, checks)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    run(parser.parse_args().root)
