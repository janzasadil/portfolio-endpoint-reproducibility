"""Validate saved empirical outputs and create a publication reporting bundle.

This module consumes completed files only.  It never forms portfolios or runs a
bootstrap, so it is safe to rerun after a frozen empirical analysis.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analysis import endpoint_summary, kaplan_meier
from .diagnostics import audit_summary, selector_fixed_method_summary
from .ingest import project_root


RUNS = {
    "17 industries": ("primary_17_definitive_B2000", "baseline_"),
    "30 industries": ("replication_30_B1000", ""),
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bootstrap_interval(draws: pd.Series) -> tuple[float, float]:
    """The saved percentile CI convention used by the study runner."""
    return tuple(float(x) for x in np.percentile(draws.to_numpy(dtype=float), [2.5, 97.5]))


def _display_bp(value: float) -> str:
    return f"{10_000 * value:.2f}"


def _display_pct(value: float) -> str:
    # ``escape=False`` is intentional for readable headers; percentages must
    # therefore be escaped explicitly for valid LaTex source.
    return f"{100 * value:.1f}\\%"


def _validate_run(root: Path, label: str, run_name: str, prefix: str) -> tuple[dict, list[dict]]:
    """Recompute point aggregates and saved percentile intervals from raw files."""
    run = root / "results" / run_name
    summary = _read_json(run / "summary.json")
    endpoint = pd.read_csv(run / "endpoint_pairs.csv", parse_dates=["earlier_endpoint", "later_endpoint"])
    selection = pd.read_csv(run / "ex_ante_selection.csv")
    checks: list[dict] = []
    direct_endpoint = endpoint_summary(endpoint)
    for key, value in direct_endpoint.items():
        checks.append({"scope": label, "check": f"endpoint aggregate: {key}",
                       "passed": bool(np.isclose(value, summary[key])), "detail": f"direct={value:.12g}; saved={summary[key]:.12g}"})
    checks.append({"scope": label, "check": "endpoint losses nonnegative", "passed": bool((endpoint.endpoint_loss >= -1e-12).all()),
                   "detail": f"minimum={endpoint.endpoint_loss.min():.3g}"})
    same_winner = endpoint.earlier_winner == endpoint.later_winner
    checks.append({"scope": label, "check": "unchanged winner implies zero endpoint loss",
                   "passed": bool(np.allclose(endpoint.loc[same_winner, "endpoint_loss"], 0, atol=1e-12)),
                   "detail": f"n unchanged={int(same_winner.sum())}"})
    for key, column in (("mean_selection_regret", "selection_regret"), ("mean_selector_minus_ensemble", "selector_minus_ensemble"),
                        ("selector_hit_rate", "selector_hit")):
        direct = float(selection[column].mean())
        checks.append({"scope": label, "check": f"ex-ante aggregate: {key}", "passed": bool(np.isclose(direct, summary[key])),
                       "detail": f"direct={direct:.12g}; saved={summary[key]:.12g}"})
    draws = pd.read_csv(run / "outer_bootstrap.csv")
    manifest = _read_json(run / "run_manifest.json")
    expected_n = int(manifest["outer_bootstrap_replications"])
    checks.append({"scope": label, "check": "completed bootstrap replication count", "passed": len(draws) == expected_n,
                   "detail": f"draws={len(draws)}; manifest={expected_n}"})
    intervals = _read_json(run / "outer_bootstrap_intervals.json")
    for saved_key, saved in intervals.items():
        column = saved_key
        direct = bootstrap_interval(draws[column])
        checks.append({"scope": label, "check": f"percentile CI: {saved_key}",
                       "passed": bool(np.allclose(direct, saved, atol=1e-15)),
                       "detail": f"direct=[{direct[0]:.12g}, {direct[1]:.12g}]"})
    result = {"summary": summary, "endpoint": endpoint, "selection": selection, "draws": draws, "prefix": prefix,
              "manifest": manifest, "run_name": run_name}
    return result, checks


def _validate_diagnostics(root: Path) -> list[dict]:
    diagnostics = root / "results" / "diagnostics"
    checks: list[dict] = []
    summary = pd.read_csv(diagnostics / "survival_validation_summary.csv")
    for row in summary.itertuples(index=False):
        name = f"survival_origin_audit_{row.specification}"
        if row.sample == "common_calendar_origins":
            name += "_common_origins"
        audit = pd.read_csv(diagnostics / f"{name}.csv", parse_dates=["origin_date", "first_failure_date"])
        direct = audit_summary(audit)
        for key in ("n_origins_full_km", "n_censored_full_km", "n_complete_12", "n_complete_24",
                    "survival_12_complete_followup", "survival_24_complete_followup", "median_survival_months_full_km"):
            actual, saved = direct[key], getattr(row, key)
            equal = (pd.isna(actual) and pd.isna(saved)) or np.isclose(actual, saved)
            checks.append({"scope": row.specification, "check": f"survival audit {row.sample}: {key}", "passed": bool(equal),
                           "detail": f"direct={actual}; saved={saved}"})
        curve = pd.read_csv(diagnostics / f"survival_curve_literal_{row.specification}.csv")
        direct_curve = kaplan_meier(audit.rename(columns={"survival_duration_months": "time_months"})[["time_months", "event"]])
        if row.sample == "specification_origins":
            equal_curve = (curve.shape == direct_curve.shape and
                           np.allclose(curve.to_numpy(dtype=float), direct_curve.to_numpy(dtype=float), atol=1e-12))
            checks.append({"scope": row.specification, "check": "literal KM curve with administrative censoring", "passed": equal_curve,
                           "detail": f"rows={len(curve)}"})
    material_summary = pd.read_csv(diagnostics / "literal_vs_material_survival_summary.csv")
    for universe in ("17", "30"):
        literal = pd.read_csv(diagnostics / f"survival_origin_audit_{universe}_baseline.csv")
        material = pd.read_csv(diagnostics / f"material_origin_audit_{universe}_baseline.csv")
        checks.append({"scope": universe, "check": "material threshold is strictly greater than 25 bp",
                       "passed": bool(material["failure_definition"].eq("material_25bp").all() and
                                      (material["loss_exceeds_threshold_exactly_12"].dropna().isin([0.0, 1.0])).all()),
                       "detail": "event rule encoded as CEQ gap > 0.0025"})
        for definition, audit in (("literal", literal), ("material_25bp", material)):
            saved = material_summary.loc[(material_summary.universe.astype(str) == universe) &
                                         (material_summary.definition == definition)].iloc[0]
            direct = audit_summary(audit)
            checks.append({"scope": universe, "check": f"{definition} survival summary", "passed": bool(np.isclose(
                direct["survival_12_complete_followup"], saved.survival_12_complete_followup)),
                           "detail": f"S12={direct['survival_12_complete_followup']:.6f}"})
    for label, (run_name, _) in RUNS.items():
        selection = pd.read_csv(diagnostics / f"ex_ante_selection_{'17_baseline' if label.startswith('17') else '30_baseline'}.csv")
        paired = selector_fixed_method_summary(selection)
        saved = pd.read_csv(diagnostics / "selector_vs_fixed_methods.csv")
        saved = saved.loc[saved.universe.astype(str) == label.split()[0]].drop(columns="universe").reset_index(drop=True)
        checks.append({"scope": label, "check": "fixed-method comparisons use identical paired decision windows",
                       "passed": paired.round(12).equals(saved.round(12)), "detail": f"n={len(selection)} per method"})
    return checks


def _publication_tables(run_data: dict[str, dict], diagnostics: Path, output: Path) -> dict:
    table1, table2 = [], []
    for label, data in run_data.items():
        prefix, summary, draws = data["prefix"], data["summary"], data["draws"]
        ci = bootstrap_interval(draws[f"{prefix}mean_endpoint_loss"])
        table1.append({"Universe": label, "Mean endpoint loss (bp)": _display_bp(summary["mean_endpoint_loss"]),
                       "95% percentile CI (bp)": f"[{_display_bp(ci[0])}, {_display_bp(ci[1])}]",
                       "Median (bp)": _display_bp(summary["median_endpoint_loss"]), "P75 (bp)": _display_bp(summary["p75_endpoint_loss"]),
                       "P90 (bp)": _display_bp(summary["p90_endpoint_loss"]), "Literal switching": _display_pct(summary["literal_switch_frequency"]),
                       "Eligible origins": int(summary["n_origins"])})
        regret_ci = bootstrap_interval(draws[f"{prefix}mean_selection_regret"])
        ensemble_ci = bootstrap_interval(draws[f"{prefix}mean_selector_minus_ensemble"])
        table2.append({"Universe": label, "Selector hit rate": _display_pct(summary["selector_hit_rate"]),
                       "Selection regret (bp)": _display_bp(summary["mean_selection_regret"]),
                       "Selection-regret CI (bp)": f"[{_display_bp(regret_ci[0])}, {_display_bp(regret_ci[1])}]",
                       "Selector − ensemble (bp)": _display_bp(summary["mean_selector_minus_ensemble"]),
                       "Selector − ensemble CI (bp)": f"[{_display_bp(ensemble_ci[0])}, {_display_bp(ensemble_ci[1])}]"})
    main1, main2 = pd.DataFrame(table1), pd.DataFrame(table2)
    main1.to_csv(output / "table_1_endpoint_reproducibility.csv", index=False)
    main2.to_csv(output / "table_2_ex_ante_recoverability.csv", index=False)
    survival = pd.read_csv(diagnostics / "literal_vs_material_survival_summary.csv")
    survival.to_csv(output / "figure_1_winner_durability_table.csv", index=False)
    displacement = pd.read_csv(diagnostics / "endpoint_displacement_profiles.csv")
    displacement.to_csv(output / "figure_2_endpoint_displacement_table.csv", index=False)
    return {"table1": table1, "table2": table2, "survival": survival, "displacement": displacement}


def _figures(diagnostics: Path, output: Path) -> None:
    """Rebuild publication figures as vector PDFs from saved diagnostic curves."""
    fig, ax = plt.subplots(figsize=(6.4, 3.7), constrained_layout=True)
    curves = (("17 industries: literal", "survival_curve_literal_17_baseline.csv"),
              ("17 industries: material >25 bp", "survival_curve_material_25bp_17_baseline.csv"),
              ("30 industries: literal", "survival_curve_literal_30_baseline.csv"),
              ("30 industries: material >25 bp", "survival_curve_material_25bp_30_baseline.csv"))
    for label, filename in curves:
        curve = pd.read_csv(diagnostics / filename)
        ax.step(np.r_[0, curve.time_months], np.r_[1.0, curve.survival], where="post", label=label)
    ax.set(xlabel="Months since December origin", ylabel="First-failure survival", ylim=(0, 1.03))
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.savefig(output / "figure_1_winner_durability.pdf")
    fig.savefig(output / "figure_1_winner_durability.png", dpi=220)
    plt.close(fig)

    table = pd.read_csv(diagnostics / "endpoint_displacement_profiles.csv")
    table = table.loc[table["sample"] == "full_eligible"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), constrained_layout=True)
    for universe, subset in table.groupby("universe"):
        subset = subset.sort_values("displacement_months")
        axes[0].plot(subset.displacement_months, 10_000 * subset.mean_endpoint_loss, marker="o", label=f"{universe} industries")
        axes[1].plot(subset.displacement_months, 100 * subset.literal_switch_frequency, marker="o", label=f"{universe} industries")
    axes[0].set(xlabel="Endpoint displacement (months)", ylabel="Mean endpoint loss (bp)")
    axes[1].set(xlabel="Endpoint displacement (months)", ylabel="Literal switching (%)")
    axes[0].legend(frameon=False)
    fig.savefig(output / "figure_2_endpoint_displacement_profiles.pdf")
    fig.savefig(output / "figure_2_endpoint_displacement_profiles.png", dpi=220)
    plt.close(fig)


def _write_tex(table: pd.DataFrame, output: Path, stem: str, caption: str, label: str, note: str) -> None:
    """Write a compact, directly pasteable LaTex table shell from audited values."""
    def format_number(value: float) -> str:
        return f"{value:.0f}" if float(value).is_integer() else f"{value:.2f}"

    body = table.to_latex(index=False, escape=False, float_format=format_number,
                          column_format="l" + "r" * (len(table.columns) - 1))
    text = "\\begin{table}[H]\n\\centering\n\\caption{" + caption + "}\n\\label{" + label + "}\n" + body
    text += "\\begin{flushleft}\\footnotesize " + note + "\\end{flushleft}\n\\end{table}\n"
    (output / f"{stem}.tex").write_text(text, encoding="utf-8")


def _write_figure_shells(output: Path) -> None:
    """Pasteable strict-placement figure wrappers (requires ``\\usepackage{float}``)."""
    figures = (
        ("figure_1_winner_durability.tex", "figure_1_winner_durability.pdf", "Winner durability", "fig:durability",
         "Literal first-switch and economically material first-failure survival. Material failure is a CEQ gap strictly greater than 25 bp."),
        ("figure_2_endpoint_displacement_profiles.tex", "figure_2_endpoint_displacement_profiles.pdf", "Endpoint-displacement profiles", "fig:displacement",
         "Mean endpoint loss and literal switching across the three saved endpoint displacements. Lines connect reported values only and do not impose a functional form."),
    )
    for filename, graphic, caption, label, note in figures:
        text = ("\\begin{figure}[H]\n\\centering\n"
                f"\\includegraphics[width=\\linewidth]{{{graphic}}}\n"
                f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
                f"\\begin{{flushleft}}\\footnotesize {note}\\end{{flushleft}}\n\\end{{figure}}\n")
        (output / filename).write_text(text, encoding="utf-8")


def _latex_tables(root: Path, diagnostics: Path, output: Path, tables: dict) -> None:
    """Create main-text and A1--A8 pasteable LaTex tables from saved outputs."""
    _write_tex(pd.DataFrame(tables["table1"]), output, "table_1_endpoint_reproducibility", "Endpoint reproducibility", "tab:endpoint", "Endpoint loss is the later-window CEQ shortfall of the earlier winner; CIs are saved percentile bootstrap intervals.")
    _write_tex(pd.DataFrame(tables["table2"]), output, "table_2_ex_ante_recoverability", "Ex-ante recoverability", "tab:recoverability", "The future candidate-set oracle is retrospective. Selector-minus-ensemble is reported on continuous implementable paths.")
    survival = tables["survival"].copy()
    a1 = pd.DataFrame({"Universe": survival.universe.astype(str) + " industries",
                       "Literal S(12)": survival.survival_12_complete_followup.map(_display_pct),
                       "Literal S(24)": survival.survival_24_complete_followup.map(_display_pct),
                       "Median literal (months)": survival.median_survival_months_full_km,
                       "Eligible origins": survival.n_origins_full_km})
    material = survival.loc[survival.definition == "material_25bp"].reset_index(drop=True)
    literal = a1.loc[survival.definition == "literal"].reset_index(drop=True)
    a1 = literal.merge(pd.DataFrame({"Universe": material.universe.astype(str) + " industries",
                                     "Material S(12)": material.survival_12_complete_followup.map(_display_pct),
                                     "Material S(24)": material.survival_24_complete_followup.map(_display_pct),
                                     "Median material (months)": material.median_survival_months_full_km}), on="Universe")
    _write_tex(a1, output, "table_A1_winner_durability", "Winner durability", "tab:durability", "Material failure is the first CEQ gap strictly greater than 25 bp; S(12) and S(24) use complete-follow-up origins.")
    validation = pd.read_csv(diagnostics / "survival_validation_summary.csv")
    a2 = validation.loc[validation["sample"] == "common_calendar_origins", ["specification", "n_origins_full_km", "median_survival_months_full_km", "survival_12_complete_followup", "survival_24_complete_followup", "winner_differs_exactly_12_complete", "first_failure_within_12_complete", "regained_by_12_complete"]].copy()
    a2.columns = ["Specification", "Common n", "Median months", "S(12)", "S(24)", "Differs at 12", "First switch by 12", "Switched and regained"]
    for col in ["S(12)", "S(24)", "Differs at 12", "First switch by 12", "Switched and regained"]:
        a2[col] = a2[col].map(_display_pct)
    _write_tex(a2, output, "table_A2_survival_validation", "Survival validation and temporary switching", "tab:survival-validation", "Matched December origins only. First switching is not reversed by later recovery.")
    a3 = tables["displacement"].copy()
    a3["mean_endpoint_loss"] = a3.mean_endpoint_loss.map(_display_bp)
    for col in ["median_endpoint_loss", "p75_endpoint_loss", "p90_endpoint_loss"]:
        a3[col] = a3[col].map(_display_bp)
    for col in ["literal_switch_frequency", "loss_exceeds_25bp_frequency"]:
        a3[col] = a3[col].map(_display_pct)
    a3 = a3.rename(columns={"universe": "Universe", "sample": "Sample", "displacement_months": "h", "mean_endpoint_loss": "Mean loss (bp)", "median_endpoint_loss": "Median (bp)", "p75_endpoint_loss": "P75 (bp)", "p90_endpoint_loss": "P90 (bp)", "literal_switch_frequency": "Switching", "loss_exceeds_25bp_frequency": "Loss >25 bp", "n_origins": "n"})
    _write_tex(a3, output, "table_A3_endpoint_displacement", "Endpoint-displacement profile", "tab:displacement", "Full and matched-calendar-origin samples are shown separately; no functional form is fitted.")
    a4 = pd.read_csv(diagnostics / "selector_vs_fixed_methods.csv")
    for col in ["mean_fixed_future_ceq", "mean_selector_minus_fixed"]:
        a4[col] = a4[col].map(_display_bp)
    for col in ["selector_better_fraction", "future_candidate_winner_frequency"]:
        a4[col] = a4[col].map(_display_pct)
    a4 = a4[["universe", "fixed_method", "n_decision_windows", "mean_fixed_future_ceq", "mean_selector_minus_fixed", "selector_better_fraction", "future_candidate_winner_frequency"]]
    a4.columns = ["Universe", "Fixed method", "Decision windows", "Future CEQ (bp)", "Selector minus method (bp)", "Selector better", "Future winner frequency"]
    _write_tex(a4, output, "table_A4_selector_fixed_methods", "Selector versus fixed methods", "tab:selector-fixed", "Descriptive paired comparisons only; no fixed method is retrospectively designated as an ex-ante rule.")
    sensitivity = pd.read_csv(output / "supplement_completed_specification_sensitivities.csv")
    sensitivity.insert(1, "L", [36, 120, 60])
    sensitivity.insert(2, "Rebalance", ["monthly", "monthly", "quarterly"])
    sensitivity.insert(3, "Cost (bp)", 25)
    sensitivity.insert(4, "gamma", 5)
    sensitivity.insert(5, "H", 120)
    sensitivity.insert(6, "h", 12)
    sensitivity["mean_endpoint_loss"] = sensitivity.mean_endpoint_loss.map(_display_bp)
    sensitivity["literal_switch_frequency"] = sensitivity.literal_switch_frequency.map(_display_pct)
    sensitivity["mean_selection_regret"] = sensitivity.mean_selection_regret.map(_display_bp)
    a5 = sensitivity[["specification", "L", "Rebalance", "Cost (bp)", "gamma", "H", "h", "mean_endpoint_loss", "literal_switch_frequency", "survival_12_months", "survival_24_months", "median_survival_months", "mean_selection_regret"]].rename(columns={"specification": "Specification", "mean_endpoint_loss": "Mean loss (bp)", "literal_switch_frequency": "Switching", "survival_12_months": "S(12)", "survival_24_months": "S(24)", "median_survival_months": "Median", "mean_selection_regret": "Selection regret (bp)"})
    for col in ["S(12)", "S(24)"]:
        a5[col] = a5[col].map(_display_pct)
    _write_tex(a5, output, "table_A5_specification_robustness", "Completed specification robustness", "tab:robustness", "Only separately completed deterministic specifications are shown. Cost and gamma variations are available as paired bootstrap draws, not as standalone saved point-estimate runs.")
    a6 = pd.read_csv(output / "supplement_bootstrap_intervals.csv")
    a6["endpoint_loss_ci_low_bp"] = a6.endpoint_loss_ci_low_bp.map(lambda x: f"{x:.2f}")
    a6["endpoint_loss_ci_high_bp"] = a6.endpoint_loss_ci_high_bp.map(lambda x: f"{x:.2f}")
    _write_tex(a6, output, "table_A6_bootstrap_robustness", "Bootstrap robustness", "tab:bootstrap", "Endpoint-loss percentile intervals from completed runs; fixed-block rows are sensitivity analyses.")
    a7 = pd.DataFrame([["Equal weight", "None", "Equal weights", "Long-only, fully invested"], ["Sample GMV", "Sample covariance", "Minimum variance", "Long-only, fully invested"], ["Ledoit--Wolf GMV", "Ledoit--Wolf shrinkage", "Minimum variance", "Long-only, fully invested"], ["Inverse volatility", "Sample volatility", "Weights proportional to inverse volatility", "Long-only, fully invested"], ["ERC", "Sample covariance", "Equal risk contributions", "Long-only, fully invested"]], columns=["Method", "Risk input", "Objective/rule", "Constraints"])
    a7["Lookback"] = "60 months"
    a7["Rebalance"] = "Monthly"
    _write_tex(a7, output, "table_A7_method_definitions", "Portfolio-method definitions", "tab:methods", "Frozen headline definitions. The separately traded ensemble averages the five target-weight rules.")
    a8_rows = []
    for label, (run, _) in RUNS.items():
        dataset = "ff_17_industry_value_weighted_monthly.csv" if label.startswith("17") else "ff_30_industry_value_weighted_monthly.csv"
        returns = pd.read_csv(root / "data" / "processed" / dataset, index_col="date", parse_dates=True)
        endpoint = pd.read_csv(root / "results" / run / "endpoint_pairs.csv")
        decisions = pd.read_csv(root / "results" / run / "ex_ante_selection.csv")
        a8_rows.append({"Universe": label, "Assets": returns.shape[1], "Source": "Kenneth R. French Data Library", "Sample": f"{returns.index.min():%Y-%m}--{returns.index.max():%Y-%m}", "OOS start": f"{returns.index[60]:%Y-%m}", "Monthly observations": len(returns), "Endpoint pairs": len(endpoint), "Ex-ante decisions": len(decisions)})
    _write_tex(pd.DataFrame(a8_rows), output, "table_A8_data_sample", "Data and sample construction", "tab:data", "Monthly value-weighted Fama--French industry portfolios; OOS start follows the 60-month frozen estimation window.")


def _supplements(root: Path, diagnostics: Path, output: Path) -> None:
    pd.read_csv(diagnostics / "survival_validation_summary.csv").to_csv(output / "supplement_survival_matched_origins.csv", index=False)
    pd.read_csv(diagnostics / "selector_vs_fixed_methods.csv").to_csv(output / "supplement_selector_fixed_methods.csv", index=False)
    pd.read_csv(diagnostics / "literal_vs_material_survival_summary.csv").to_csv(output / "supplement_material_survival.csv", index=False)
    pd.read_csv(diagnostics / "endpoint_displacement_profiles.csv").to_csv(output / "supplement_endpoint_displacement_detail.csv", index=False)
    rows = []
    for name, label in (("primary_17_L36", "L=36"), ("primary_17_L120", "L=120"), ("primary_17_quarterly", "Quarterly")):
        values = _read_json(root / "results" / name / "summary.json")
        rows.append({"specification": label, **values})
    pd.DataFrame(rows).to_csv(output / "supplement_completed_specification_sensitivities.csv", index=False)
    boot_rows = []
    for name, method in (("primary_17_definitive_B2000", "stationary (enhanced baseline)"),
                         ("replication_30_B1000", "stationary"), ("primary_17_fixedblock12_B1000", "fixed circular block, 12 months"),
                         ("primary_17_fixedblock24_B1000", "fixed circular block, 24 months")):
        manifest = _read_json(root / "results" / name / "run_manifest.json")
        interval = _read_json(root / "results" / name / "outer_bootstrap_intervals.json")
        key = "baseline_mean_endpoint_loss" if name == "primary_17_definitive_B2000" else "mean_endpoint_loss"
        boot_rows.append({"run": name, "bootstrap_method": method, "replications": manifest["outer_bootstrap_replications"],
                          "endpoint_loss_ci_low_bp": 10000 * interval[key][0], "endpoint_loss_ci_high_bp": 10000 * interval[key][1]})
    pd.DataFrame(boot_rows).to_csv(output / "supplement_bootstrap_intervals.csv", index=False)


def _markdown_bundle(output: Path, checks: list[dict], tables: dict) -> None:
    failed = [check for check in checks if not check["passed"]]
    validation = ["# Final validation report", "", "## Scope", "", "This report was regenerated from saved empirical and diagnostic outputs. No portfolio paths or bootstrap draws were created.",
                  "", "## Audit outcome", "", f"{len(checks) - len(failed)}/{len(checks)} direct checks passed."]
    if failed:
        validation += ["", "## Discrepancies requiring review", ""] + [f"- **{x['scope']} — {x['check']}**: {x['detail']}" for x in failed]
    else:
        validation += ["", "No computational or reporting discrepancy was found in the audited saved outputs."]
    validation += ["", "## Important distinctions and limitations", "", "- The original baseline survival summary is a censored KM estimate; the audit's headline S(12)/S(24) uses complete-follow-up origin cohorts. Common-origin robustness comparisons are separate and must not replace baseline estimates.", "- The economic-material event is a first monthly CEQ gap strictly greater than 25 bp; it is not literal switching or an exact-month-12 event.", "- Bootstrap CIs are percentile intervals from completed runs: stationary B=2,000 (17 industries), stationary B=1,000 (30 industries), and fixed circular-block B=1,000 sensitivity runs. They do not establish differences across specifications.", "- The two industry universes share underlying equity histories and are not independent replications.", "", "## Unavailable inference and recommendation", "", "Formal claims about differences between baseline and L=36/L=120/quarterly survival or displacement profiles require paired outer-bootstrap differences. The minimum useful additional computation is a single paired stationary-bootstrap run (at least B=1,000) that evaluates the existing specifications on the same pseudo-histories. It was not run here."]
    (output / "FINAL_VALIDATION_REPORT.md").write_text("\n".join(validation) + "\n", encoding="utf-8")
    t1, t2 = pd.DataFrame(tables["table1"]), pd.DataFrame(tables["table2"])
    draft = ["# Results", "", "## Endpoint reproducibility", "", "Table 1 reports endpoint sensitivity using the frozen 120-month evaluation horizon. In the 17-industry universe, mean 12-month endpoint loss was " + t1.iloc[0]["Mean endpoint loss (bp)"] + " bp (95% percentile interval " + t1.iloc[0]["95% percentile CI (bp)"] + "); the literal switching frequency was " + t1.iloc[0]["Literal switching"] + ". In the 30-industry universe, the corresponding values were " + t1.iloc[1]["Mean endpoint loss (bp)"] + " bp (" + t1.iloc[1]["95% percentile CI (bp)"] + ") and " + t1.iloc[1]["Literal switching"] + ". These universes share underlying equity histories and are therefore not independent replications.", "", "## Winner durability and economic materiality", "", "Literal winner switching is distinct from first-switch survival, which records the first month in which the original winner loses first place and is not reversed by later recovery. It is also distinct from the previously specified secondary diagnostic of a first CEQ loss strictly exceeding 25 bp. Figure 1 and its accompanying table report both curves with complete-follow-up S(12)/S(24) summaries and administratively censored KM curves. The increased prominence of the materiality diagnostic follows inspection of the completed results; it should therefore be interpreted as secondary evidence.", "", "## Ex-ante recoverability", "", "Table 2 evaluates preceding-performance selection on subsequent fixed windows. The selector's future candidate-set oracle is retrospective and not implementable; historical endpoint loss is likewise not future investment regret. The selector-minus-ensemble comparisons are implementable-path comparisons, whereas fixed-method contrasts are descriptive paired benchmarks without new dependence-aware inference. No significance statements are made from these summaries.", "", "The completed lookback, rebalancing, fixed-block, and matched-origin analyses are reported in the supplement. Descriptive differences across these specifications are not statistically established differences without paired inference."]
    (output / "RESULTS_SECTION_DRAFT.md").write_text("\n".join(draft) + "\n", encoding="utf-8")


def run_reporting(output_dir: Path | None = None) -> Path:
    root = project_root()
    output = output_dir or root / "results" / "publication"
    output.mkdir(parents=True, exist_ok=True)
    run_data, checks = {}, []
    for label, (run, prefix) in RUNS.items():
        run_data[label], run_checks = _validate_run(root, label, run, prefix)
        checks.extend(run_checks)
    checks.extend(_validate_diagnostics(root))
    pd.DataFrame(checks).to_csv(output / "validation_checks.csv", index=False)
    diagnostics = root / "results" / "diagnostics"
    tables = _publication_tables(run_data, diagnostics, output)
    _figures(diagnostics, output)
    _supplements(root, diagnostics, output)
    _latex_tables(root, diagnostics, output, tables)
    _write_figure_shells(output)
    _markdown_bundle(output, checks, tables)
    final = {"validation": {"checks": len(checks), "failures": sum(not c["passed"] for c in checks)},
             "main_tables": {"endpoint_reproducibility": tables["table1"], "ex_ante_recoverability": tables["table2"]},
             "bootstrap_runs": {label: {"run": d["run_name"], "replications": d["manifest"]["outer_bootstrap_replications"]} for label, d in run_data.items()},
             "limitations": "No paired bootstrap differences were run for robustness comparisons."}
    (output / "FINAL_RESULTS_SUMMARY.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Default: results/publication")
    args = parser.parse_args()
    print(run_reporting(args.output_dir))


if __name__ == "__main__":
    main()
