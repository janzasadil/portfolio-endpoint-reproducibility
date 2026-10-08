"""Retrospective fixed-label and fixed-method benchmarks from saved CEQs.

Reads only prospective-analysis artifacts. No portfolio paths, CEQ windows,
endpoint analyses, or bootstrap replications are recomputed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER, _winner
from .ingest import project_root

ATOL = 1e-12
SAMPLES = {
    "17_industries": ("primary_17_definitive_B2000", 75, "38.7", "109.12"),
    "14_countries": ("country_replication_B1000", 27, "25.9", "48.25"),
}
METHOD_LABELS = {
    "equal_weight": "Equal weight",
    "sample_gmv": "Sample GMV",
    "ledoit_wolf_gmv": "Ledoit–Wolf GMV",
    "inverse_volatility": "Inverse volatility",
    "erc": "ERC",
}


def benchmark_selection(
    selection: pd.DataFrame,
    sample: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """Validate saved labels/regrets, then compare five fixed choices.

    Future-best shares count the deterministic reported winner, not all methods
    attaining the maximum in a tie. Benchmark objective ties also use the
    frozen method order, with all tied choices disclosed in the summary.
    """
    if selection.empty:
        raise ValueError("No prospective decision dates")
    dates = pd.DatetimeIndex(pd.to_datetime(selection.decision_date))
    if dates.has_duplicates or not dates.is_monotonic_increasing or (dates.month != 12).any():
        raise ValueError("Decision dates must be unique, ordered December dates")
    if len(dates) > 1 and not np.all(np.diff(dates.year) == 1):
        raise ValueError("Annual decision-date sequence has a missing year")
    score_columns = [f"{prefix}_ceq_{m}" for prefix in ("past", "future") for m in TIE_BREAK_ORDER]
    if not np.isfinite(selection[score_columns].to_numpy(dtype=float)).all():
        raise ValueError("Saved CEQs must all be finite")
    if selection.selector_hit.dtype != bool:
        raise ValueError("Saved selector-hit flags must be Boolean")
    records, tie_records = [], []
    for _, row in selection.iterrows():
        past = {m: float(row[f"past_ceq_{m}"]) for m in TIE_BREAK_ORDER}
        future = {m: float(row[f"future_ceq_{m}"]) for m in TIE_BREAK_ORDER}
        selected = _winner(past)[0]
        oracle, best, _ = _winner(future)
        if selected != row.selected_method or oracle != row.future_oracle:
            raise ValueError("Saved prospective labels conflict with the frozen tie rule")
        hit = selected == oracle
        if hit != row.selector_hit:
            raise ValueError("Saved selector hit conflicts with method labels")
        regret = best - future[selected]
        saved_regret = float(row.selection_regret)
        if not np.isfinite(saved_regret) or abs(regret - saved_regret) > ATOL:
            raise ValueError("Saved selector regret conflicts with following-window CEQs")
        ties = [m for m in TIE_BREAK_ORDER if future[m] == best]
        date = pd.Timestamp(row.decision_date)
        period = date.to_period("M")
        record = {
            "sample": sample,
            "decision_date": date,
            "past_window_start": (period - 119).to_timestamp("M"),
            "past_window_end": date,
            "future_window_start": (period + 1).to_timestamp("M"),
            "future_window_end": (period + 120).to_timestamp("M"),
            "selected_method": selected,
            "future_best_method": oracle,
            "selector_hit": hit,
            "selector_regret_bp": regret * 10000,
            **{f"future_ceq_{m}": future[m] for m in TIE_BREAK_ORDER},
            **{f"fixed_regret_bp_{m}": (best - future[m]) * 10000 for m in TIE_BREAK_ORDER},
        }
        records.append(record)
        if len(ties) > 1:
            tie_records.append(
                {
                    "sample": sample,
                    "decision_date": date,
                    "reported_future_best_method": oracle,
                    "tied_methods": json.dumps(ties),
                    **future,
                }
            )
    decisions = pd.DataFrame(records)
    n = len(decisions)
    counts = {m: int(decisions.future_best_method.eq(m).sum()) for m in TIE_BREAK_ORDER}
    means = {m: float(decisions[f"fixed_regret_bp_{m}"].mean()) for m in TIE_BREAK_ORDER}
    majority = _winner(counts)[0]
    best_fixed = _winner({m: -means[m] for m in TIE_BREAK_ORDER})[0]
    selector_hit = float(decisions.selector_hit.mean())
    selector_regret = float(decisions.selector_regret_bp.mean())
    summary = {
        "sample": sample,
        "horizon_months": 120,
        "n_decisions": n,
        "first_decision_date": dates[0].date().isoformat(),
        "last_decision_date": dates[-1].date().isoformat(),
        "preceding_winner_hit_rate": selector_hit,
        "majority_constant_hit_rate": counts[majority] / n,
        "difference_pp": 100 * (selector_hit - counts[majority] / n),
        "majority_method": majority,
        "tied_majority_methods": [m for m in TIE_BREAK_ORDER if counts[m] == counts[majority]],
        "preceding_winner_mean_regret_bp": selector_regret,
        "best_fixed_method": best_fixed,
        "best_fixed_mean_regret_bp": means[best_fixed],
        "selector_minus_best_fixed_regret_bp": selector_regret - means[best_fixed],
        "tied_best_fixed_methods": [m for m in TIE_BREAK_ORDER if means[m] == means[best_fixed]],
        "majority_method_is_best_fixed_method": majority == best_fixed,
        "future_best_tie_dates": len(tie_records),
        "max_saved_regret_residual": float(
            np.max(
                np.abs(
                    decisions.selector_regret_bp.to_numpy() / 10000
                    - selection.selection_regret.to_numpy()
                )
            )
        ),
    }
    base_rates = pd.DataFrame(
        [
            {
                "sample": sample,
                "method": m,
                "future_best_count": counts[m],
                "future_best_share": counts[m] / n,
                "future_best_percent": 100 * counts[m] / n,
            }
            for m in TIE_BREAK_ORDER
        ]
    )
    fixed_regrets = pd.DataFrame(
        [
            {
                "sample": sample,
                "method": m,
                "mean_regret_bp": means[m],
                "median_regret_bp": float(decisions[f"fixed_regret_bp_{m}"].median()),
                "future_best_share": counts[m] / n,
            }
            for m in TIE_BREAK_ORDER
        ]
    )
    ties = pd.DataFrame(
        tie_records,
        columns=[
            "sample",
            "decision_date",
            "reported_future_best_method",
            "tied_methods",
            *TIE_BREAK_ORDER,
        ],
    )
    return base_rates, fixed_regrets, summary, ties, decisions


def validate_headlines(summary: dict, saved_summary: dict, expected: tuple) -> None:
    """Check rounded manuscript values and exact frozen numerical summaries."""
    _, count, hit_percent, regret_bp = expected
    if summary["n_decisions"] != count:
        raise ValueError(
            f"Decision count mismatch: expected {count}, found {summary['n_decisions']}"
        )
    if f"{100 * summary['preceding_winner_hit_rate']:.1f}" != hit_percent:
        raise ValueError("Correct-selection headline does not reproduce")
    if f"{summary['preceding_winner_mean_regret_bp']:.2f}" != regret_bp:
        raise ValueError("Mean selection-regret headline does not reproduce")
    for actual, reference in (
        (summary["preceding_winner_hit_rate"], saved_summary["selector_hit_rate"]),
        (
            summary["preceding_winner_mean_regret_bp"] / 10000,
            saved_summary["mean_selection_regret"],
        ),
    ):
        if not np.isfinite(reference) or abs(actual - reference) > ATOL:
            raise ValueError("Prospective results differ from the frozen summary")


def make_report(base_rates, fixed_regrets, summaries) -> str:
    lines = [
        "# Fixed-method and base-rate benchmark",
        "",
        "H=120; the existing annual December decision dates and saved preceding/following-window CEQs "
        "are reused without changing holdings, costs, windows, or candidate methods. Shares in the CSVs "
        "are native proportions; this report displays percentages. Both benchmark choices use the "
        "realized following-window sample and are retrospective descriptive benchmarks, not deployable selectors.",
        "",
        "## Table A — Future-best base rates",
        "",
    ]
    for sample, summary in summaries.items():
        lines += [
            f"### {sample} (D={summary['n_decisions']})",
            "",
            "| Method | Future-best count | Future-best share |",
            "|---|---:|---:|",
        ]
        for row in base_rates.loc[base_rates["sample"] == sample].itertuples():
            lines.append(
                f"| {METHOD_LABELS[row.method]} | {row.future_best_count} | {100 * row.future_best_share:.1f}% |"
            )
        lines += [
            "",
            f"Preceding-winner hit rate: **{100 * summary['preceding_winner_hit_rate']:.1f}%**; "
            f"majority constant-label rate: **{100 * summary['majority_constant_hit_rate']:.1f}%** "
            f"({METHOD_LABELS[summary['majority_method']]}); difference: "
            f"**{summary['difference_pp']:+.1f} percentage points**.",
            "",
        ]
    lines += ["## Table B — Fixed-method regret", ""]
    for sample, summary in summaries.items():
        lines += [
            f"### {sample}",
            "",
            "| Method | Mean regret (CEQ bp) | Median regret (CEQ bp) | Future-best share |",
            "|---|---:|---:|---:|",
        ]
        for row in fixed_regrets.loc[fixed_regrets["sample"] == sample].itertuples():
            lines.append(
                f"| {METHOD_LABELS[row.method]} | {row.mean_regret_bp:.2f} | {row.median_regret_bp:.2f} | {100 * row.future_best_share:.1f}% |"
            )
        lines += [
            "",
            f"Preceding-winner mean regret: **{summary['preceding_winner_mean_regret_bp']:.2f} bp**; "
            f"best fixed method: **{METHOD_LABELS[summary['best_fixed_method']]}**, with mean regret "
            f"**{summary['best_fixed_mean_regret_bp']:.2f} bp**; selector minus best fixed: "
            f"**{summary['selector_minus_best_fixed_regret_bp']:+.2f} bp**.",
            "",
            f"Majority label also minimizes mean fixed-method regret: "
            f"**{summary['majority_method_is_best_fixed_method']}**. "
            f"Future-best exact CEQ ties: **{summary['future_best_tie_dates']} dates**. "
            f"All majority objective ties: {', '.join(summary['tied_majority_methods'])}; "
            f"all minimum-regret objective ties: {', '.join(summary['tied_best_fixed_methods'])}.",
            "",
        ]
    lines += [
        "## Validation and interpretation",
        "",
        "Both decision counts and all four requested headline values reproduced. Unrounded hit "
        "rates and regrets match the frozen summaries within 1e-12 native CEQ/proportion units. "
        "Every saved selected method, future-best label, selector hit, and regret is checked against "
        "the persisted CEQs using the existing exact deterministic method ordering. Exact future-best "
        "ties count as one reported label, not multiple hits; tie details are in the tie-audit CSV.",
        "",
    ]
    for sample, summary in summaries.items():
        hit_direction = (
            "above"
            if summary["difference_pp"] > 0
            else "below" if summary["difference_pp"] < 0 else "equal to"
        )
        regret_direction = (
            "higher than"
            if summary["selector_minus_best_fixed_regret_bp"] > 0
            else "lower than" if summary["selector_minus_best_fixed_regret_bp"] < 0 else "equal to"
        )
        lines.append(
            f"{sample}: the preceding-window winner's hit rate is {hit_direction} the "
            f"retrospectively chosen majority base rate, and its mean regret is {regret_direction} "
            "the retrospectively chosen best fixed method's regret."
        )
    if all(
        summary["difference_pp"] <= 0 and summary["selector_minus_best_fixed_regret_bp"] >= 0
        for summary in summaries.values()
    ):
        lines += [
            "",
            "On these two descriptive criteria, the preceding-window winner offers no "
            "performance advantage over the hindsight-selected fixed-method benchmarks in either sample. "
            "This does not prove an absence of prospective information.",
        ]
    lines += [
        "",
        "These comparisons assess incremental descriptive performance against generally strong "
        "methods; they do not establish predictive skill or statistical significance. The benchmark "
        "choices use hindsight, and overlapping following windows are not independent. No bootstrap "
        "or other expensive computation ran, and existing empirical/publication files were not modified.",
    ]
    return "\n".join(lines) + "\n"


def run(root: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(
            "Use a new benchmark-results directory; existing outputs are preserved"
        )
    rates, regrets, ties, decisions, summaries, inputs = [], [], [], [], {}, []
    for sample, expected in SAMPLES.items():
        folder = root / "results" / expected[0]
        selection = pd.read_csv(
            folder / "ex_ante_selection.csv",
            parse_dates=["decision_date"],
            float_precision="round_trip",
        )
        saved_summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        base, fixed, summary, tie_audit, decision_audit = benchmark_selection(selection, sample)
        validate_headlines(summary, saved_summary, expected)
        rates.append(base)
        regrets.append(fixed)
        ties.append(tie_audit)
        decisions.append(decision_audit)
        summaries[sample] = summary
        inputs.extend(
            (folder / name).relative_to(root).as_posix()
            for name in ("ex_ante_selection.csv", "summary.json")
        )
    rates, regrets = pd.concat(rates, ignore_index=True), pd.concat(regrets, ignore_index=True)
    output.mkdir(parents=True)
    rates.to_csv(output / "future_best_base_rates.csv", index=False)
    regrets.to_csv(output / "fixed_method_regret.csv", index=False)
    pd.DataFrame(summaries.values()).to_csv(output / "benchmark_summary.csv", index=False)
    pd.concat(ties, ignore_index=True).to_csv(output / "future_best_tie_audit.csv", index=False)
    pd.concat(decisions, ignore_index=True).to_csv(
        output / "decision_level_benchmarks.csv", index=False
    )
    payload = {
        "samples": summaries,
        "future_best_base_rates": rates.to_dict(orient="records"),
        "fixed_method_regrets": regrets.to_dict(orient="records"),
        "input_files": inputs,
        "tie_break_order": list(TIE_BREAK_ORDER),
        "validation_atol": ATOL,
        "scope": "Saved prospective CEQs only; retrospective descriptive benchmarks; no portfolio or bootstrap computation",
    }
    (output / "benchmark_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (output / "FIXED_METHOD_BENCHMARK_REPORT.md").write_text(
        make_report(rates, regrets, summaries), encoding="utf-8"
    )
    print(f"Finished: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = project_root()
    run(root, args.output_dir or root / "results/fixed_method_benchmark")


if __name__ == "__main__":
    main()
