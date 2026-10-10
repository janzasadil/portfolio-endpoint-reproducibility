"""Deterministic exploratory diagnostics for the frozen endpoint study.

These routines do not alter the frozen estimands or invoke resampling.  They
operate on the same continuous candidate return paths as the primary study.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from .analysis import (
    TIE_BREAK_ORDER,
    _winner,
    candidate_return_matrix,
    ceq,
    endpoint_reproducibility,
    ex_ante_selection,
    kaplan_meier,
)
from .engine import PathResult, run_headline_paths
from .ingest import project_root


def monthly_winner_identities(
    paths: Mapping[str, PathResult], horizon: int = 120, gamma: float = 5.0,
) -> pd.DataFrame:
    """Reconstruct winner and all candidate CEQs at every valid monthly endpoint."""
    returns = candidate_return_matrix(paths)
    records: list[dict[str, object]] = []
    for pos in range(horizon - 1, len(returns)):
        scores = {name: ceq(returns[name].iloc[pos - horizon + 1 : pos + 1], gamma)
                  for name in TIE_BREAK_ORDER}
        winner, best, margin = _winner(scores)
        records.append({"endpoint": returns.index[pos], "winner": winner,
                        "best_ceq": best, "winner_margin": margin, **scores})
    return pd.DataFrame.from_records(records).set_index("endpoint")


def _eligible_origins(winners: pd.DataFrame, december_only: bool, origin_dates: Iterable[pd.Timestamp] | None) -> pd.DataFrame:
    result = winners.copy()
    if december_only:
        result = result.loc[result.index.month == 12]
    if origin_dates is not None:
        wanted = pd.DatetimeIndex(origin_dates)
        result = result.loc[result.index.intersection(wanted)]
    return result


def survival_audit_from_winners(
    winners: pd.DataFrame,
    *,
    december_only: bool = True,
    origin_dates: Iterable[pd.Timestamp] | None = None,
    material_threshold: float | None = None,
) -> pd.DataFrame:
    """First failure audit from a monthly winner/CEQ panel.

    With ``material_threshold`` omitted, failure is the first month that the
    original winner differs.  Otherwise it is the first month its CEQ gap from
    the contemporaneous best exceeds the fixed threshold.  The original winner
    is never reset after a recovery.
    """
    required = {"winner", "best_ceq"}
    if material_threshold is not None:
        required |= set(TIE_BREAK_ORDER)
    if not required.issubset(winners.columns):
        raise ValueError(f"Winner panel missing columns: {sorted(required - set(winners.columns))}")
    panel = winners.sort_index()
    origins = _eligible_origins(panel, december_only, origin_dates)
    records: list[dict[str, object]] = []
    for date, row in origins.iterrows():
        pos = panel.index.get_loc(date)
        original = str(row["winner"])
        later = panel.iloc[pos + 1 :]
        if material_threshold is None:
            failed = later["winner"].ne(original)
            loss_at_12 = (None if len(later) < 12 else float(later.iloc[11]["winner"] != original))
        else:
            gaps = later["best_ceq"] - later[original]
            failed = gaps.gt(material_threshold)
            loss_at_12 = None if len(later) < 12 else float(gaps.iloc[11] > material_threshold)
        first_offset = np.flatnonzero(failed.to_numpy())
        event = bool(len(first_offset))
        duration = int(first_offset[0] + 1) if event else int(len(later))
        switch_date = panel.index[pos + duration] if event else pd.NaT
        winner_at_12 = str(later.iloc[11]["winner"]) if len(later) >= 12 else pd.NA
        exact_12 = pd.NA if len(later) < 12 else bool(winner_at_12 != original)
        first_within_12 = pd.NA if len(later) < 12 else bool(event and duration <= 12)
        regained = (pd.NA if len(later) < 12 else bool(event and duration <= 12 and winner_at_12 == original))
        records.append({
            "origin_date": date, "original_winner": original,
            "first_failure_date": switch_date, "event": event,
            "censored": not event, "survival_duration_months": duration,
            "available_followup_months": int(len(later)), "winner_at_12": winner_at_12,
            "winner_differs_exactly_12": exact_12,
            "first_failure_within_12": first_within_12,
            "regained_by_12": regained,
            "failure_definition": "literal" if material_threshold is None else "material_25bp",
            "loss_exceeds_threshold_exactly_12": loss_at_12,
        })
    return pd.DataFrame.from_records(records)


def _survival_probability(audit: pd.DataFrame, months: int, complete_only: bool) -> tuple[float, int]:
    sample = audit.loc[audit["available_followup_months"] >= months] if complete_only else audit
    if sample.empty:
        return float("nan"), 0
    # On complete follow-up cohorts this is the direct survival proportion,
    # equivalent to KM at the requested horizon without administrative censoring.
    survived = ~((sample["event"]) & (sample["survival_duration_months"] <= months))
    return float(survived.mean()), int(len(sample))


def audit_summary(audit: pd.DataFrame) -> dict[str, float | int]:
    """Full-KM plus complete-follow-up headline survival summaries."""
    if audit.empty:
        raise ValueError("Audit has no origins")
    km_input = audit.rename(columns={"survival_duration_months": "time_months"})[["time_months", "event"]]
    curve = kaplan_meier(km_input)
    s12, n12 = _survival_probability(audit, 12, complete_only=True)
    s24, n24 = _survival_probability(audit, 24, complete_only=True)
    complete12 = audit.loc[audit.available_followup_months >= 12]
    exact_failure = (complete12["winner_differs_exactly_12"] if audit["failure_definition"].iloc[0] == "literal"
                     else complete12["loss_exceeds_threshold_exactly_12"])
    crossed = curve.loc[curve["survival"] <= .5, "time_months"]
    return {
        "n_origins_full_km": int(len(audit)), "n_censored_full_km": int(audit["censored"].sum()),
        "n_events_full_km": int(audit["event"].sum()), "n_complete_12": n12, "n_complete_24": n24,
        "survival_12_complete_followup": s12, "survival_24_complete_followup": s24,
        "median_survival_months_full_km": float(crossed.iloc[0]) if not crossed.empty else float("nan"),
        "winner_differs_exactly_12_complete": float(complete12["winner_differs_exactly_12"].mean()),
        "failure_exactly_12_complete": float(exact_failure.mean()),
        "first_failure_within_12_complete": float(complete12["first_failure_within_12"].mean()),
        "regained_by_12_complete": float(complete12["regained_by_12"].mean()),
    }


def selector_fixed_method_summary(selection: pd.DataFrame) -> pd.DataFrame:
    """Paired descriptive selector comparisons against every fixed candidate."""
    if selection.empty:
        raise ValueError("Selection table has no decision windows")
    selected = selection.apply(lambda row: row[f"future_ceq_{row.selected_method}"], axis=1)
    rows = []
    for method in TIE_BREAK_ORDER:
        difference = selected - selection[f"future_ceq_{method}"]
        rows.append({
            "fixed_method": method, "n_decision_windows": len(selection),
            "mean_fixed_future_ceq": float(selection[f"future_ceq_{method}"].mean()),
            "mean_selector_future_ceq": float(selected.mean()),
            "mean_selector_minus_fixed": float(difference.mean()),
            "median_selector_minus_fixed": float(difference.median()),
            "p25_selector_minus_fixed": float(difference.quantile(.25)),
            "p75_selector_minus_fixed": float(difference.quantile(.75)),
            "selector_better_fraction": float((difference > 0).mean()),
            "future_candidate_winner_frequency": float((selection["future_oracle"] == method).mean()),
        })
    return pd.DataFrame.from_records(rows)


def displacement_summary(table: pd.DataFrame) -> dict[str, float | int]:
    loss = table["endpoint_loss"]
    return {"mean_endpoint_loss": float(loss.mean()), "median_endpoint_loss": float(loss.median()),
            "p75_endpoint_loss": float(loss.quantile(.75)), "p90_endpoint_loss": float(loss.quantile(.90)),
            "literal_switch_frequency": float(table["literal_switch"].mean()),
            "loss_exceeds_25bp_frequency": float((loss > .0025).mean()), "n_origins": int(len(table))}


def _write_curve(audit: pd.DataFrame, path: Path) -> None:
    curve = kaplan_meier(audit.rename(columns={"survival_duration_months": "time_months"})[["time_months", "event"]])
    curve.to_csv(path, index=False)


def _save_displacement_figure(table: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), constrained_layout=True)
    for universe, subset in table.groupby("universe"):
        subset = subset.sort_values("displacement_months")
        axes[0].plot(subset.displacement_months, 10_000 * subset.mean_endpoint_loss, marker="o", label=universe)
        axes[1].plot(subset.displacement_months, 100 * subset.literal_switch_frequency, marker="o", label=universe)
    axes[0].set(xlabel="Endpoint displacement (months)", ylabel="Mean CEQ loss (bp)")
    axes[1].set(xlabel="Endpoint displacement (months)", ylabel="Literal switch frequency (%)")
    axes[0].legend(frameon=False)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _save_survival_figure(curves: dict[str, pd.DataFrame], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 3.6), constrained_layout=True)
    for label, curve in curves.items():
        x = np.r_[0, curve.time_months.to_numpy()]
        y = np.r_[1.0, curve.survival.to_numpy()]
        ax.step(x, y, where="post", label=label)
    ax.set(xlabel="Months since December origin", ylabel="First-failure survival", ylim=(0, 1.03))
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_diagnostics(output_dir: Path | None = None, *, root: Path | None = None) -> Path:
    """Run the requested deterministic audit and write self-contained outputs."""
    root = project_root(root)
    output_dir = output_dir or root / "results" / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    with (root / "config" / "paper_design.yaml").open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    study = config["study"]
    horizon, gamma, cost = study["evaluation_horizon_months"], study["ceq_risk_aversion"], study["transaction_cost_per_half_turnover"]
    specs = [
        ("17_baseline", "primary_17_industry", 60, 1),
        ("17_L36", "primary_17_industry", 36, 1),
        ("17_L120", "primary_17_industry", 120, 1),
        ("17_quarterly", "primary_17_industry", 60, 3),
        ("30_baseline", "replication_30_industry", 60, 1),
    ]
    paths_by_spec: dict[str, dict[str, PathResult]] = {}
    winners_by_spec: dict[str, pd.DataFrame] = {}
    for label, dataset_key, lookback, rebalance in specs:
        dataset = config["datasets"][dataset_key]
        returns = pd.read_csv(root / "data" / "processed" / dataset["processed_file"], index_col="date", parse_dates=True)
        paths_by_spec[label] = run_headline_paths(returns, lookback, cost, rebalance)
        winners_by_spec[label] = monthly_winner_identities(paths_by_spec[label], horizon, gamma)

    # Specific and matched-calendar survival audits for the four 17-industry specifications.
    comparative = ["17_baseline", "17_L36", "17_L120", "17_quarterly"]
    common_dates = set(winners_by_spec[comparative[0]].index[winners_by_spec[comparative[0]].index.month == 12])
    for label in comparative[1:]:
        dates = winners_by_spec[label].index[winners_by_spec[label].index.month == 12]
        common_dates &= set(dates)
    survival_rows, curves = [], {}
    for label in specs:
        name = label[0]
        literal = survival_audit_from_winners(winners_by_spec[name])
        literal.to_csv(output_dir / f"survival_origin_audit_{name}.csv", index=False)
        _write_curve(literal, output_dir / f"survival_curve_literal_{name}.csv")
        curves[name] = kaplan_meier(literal.rename(columns={"survival_duration_months": "time_months"})[["time_months", "event"]])
        survival_rows.append({"specification": name, "sample": "specification_origins", "definition": "literal", **audit_summary(literal)})
        if name in comparative:
            matched = survival_audit_from_winners(winners_by_spec[name], origin_dates=sorted(common_dates))
            matched.to_csv(output_dir / f"survival_origin_audit_{name}_common_origins.csv", index=False)
            survival_rows.append({"specification": name, "sample": "common_calendar_origins", "definition": "literal", **audit_summary(matched)})
    pd.DataFrame(survival_rows).to_csv(output_dir / "survival_validation_summary.csv", index=False)
    _save_survival_figure({key: curves[key] for key in comparative}, output_dir / "survival_curves_17_specifications.png")

    # Material first-failure diagnostic for the two frozen baseline universes.
    material_rows, material_curves = [], {}
    for name in ("17_baseline", "30_baseline"):
        literal = survival_audit_from_winners(winners_by_spec[name])
        material = survival_audit_from_winners(winners_by_spec[name], material_threshold=.0025)
        material.to_csv(output_dir / f"material_origin_audit_{name}.csv", index=False)
        _write_curve(material, output_dir / f"survival_curve_material_25bp_{name}.csv")
        material_rows.extend([
            {"universe": name[:2], "definition": "literal", **audit_summary(literal)},
            {"universe": name[:2], "definition": "material_25bp", **audit_summary(material)},
        ])
        material_curves[f"{name} literal"] = kaplan_meier(literal.rename(columns={"survival_duration_months": "time_months"})[["time_months", "event"]])
        material_curves[f"{name} material >25bp"] = kaplan_meier(material.rename(columns={"survival_duration_months": "time_months"})[["time_months", "event"]])
    pd.DataFrame(material_rows).to_csv(output_dir / "literal_vs_material_survival_summary.csv", index=False)
    _save_survival_figure(material_curves, output_dir / "literal_vs_material_survival_curves.png")

    # Ex-ante fixed-method comparisons, descriptive only.
    selector_rows = []
    for name in ("17_baseline", "30_baseline"):
        selection = ex_ante_selection(paths_by_spec[name], horizon, gamma)
        selection.to_csv(output_dir / f"ex_ante_selection_{name}.csv", index=False)
        result = selector_fixed_method_summary(selection)
        result.insert(0, "universe", name[:2])
        selector_rows.append(result)
    pd.concat(selector_rows, ignore_index=True).to_csv(output_dir / "selector_vs_fixed_methods.csv", index=False)

    # Full and matched endpoint-displacement profiles for both universes.
    displacement_rows = []
    for name in ("17_baseline", "30_baseline"):
        endpoint_tables = {h: endpoint_reproducibility(paths_by_spec[name], horizon, h, gamma) for h in (6, 12, 24)}
        common = set.intersection(*(set(table.earlier_endpoint) for table in endpoint_tables.values()))
        for h, table in endpoint_tables.items():
            for sample, subset in (("full_eligible", table), ("common_calendar_origins", table.loc[table.earlier_endpoint.isin(common)])):
                displacement_rows.append({"universe": name[:2], "sample": sample, "displacement_months": h,
                                          **displacement_summary(subset)})
    displacement = pd.DataFrame(displacement_rows)
    displacement.to_csv(output_dir / "endpoint_displacement_profiles.csv", index=False)
    _save_displacement_figure(displacement.loc[displacement["sample"] == "full_eligible"], output_dir / "endpoint_displacement_profiles.png")

    report = {
        "status": "deterministic exploratory diagnostics; no bootstrap executed",
        "frozen_inputs": {"horizon_months": horizon, "gamma": gamma, "cost": cost},
        "common_17_survival_calendar_origin_count": len(common_dates),
        "outputs": "CSV summaries, origin-level audits, KM curves, and PNG figures in this directory",
    }
    (output_dir / "diagnostics_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Default: results/diagnostics")
    args = parser.parse_args()
    print(run_diagnostics(args.output_dir))


if __name__ == "__main__":
    main()
