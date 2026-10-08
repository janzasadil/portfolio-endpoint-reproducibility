"""Generate the lean Finance Research Letters publication bundle."""

from __future__ import annotations
import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from .analysis import kaplan_meier
from .ingest import project_root


def to_basis_points(value):
    """Convert a native-unit return to basis points without rounding."""
    return 10000 * value


def to_percent(value):
    """Convert a proportion to a percentage without rounding."""
    return 100 * value


def format_tabular(frame, column_format=None):
    formatted = frame.copy()
    formatted.columns = [
        str(column).replace("%", r"\%").replace("_", r"\_")
        for column in formatted.columns
    ]
    for column in formatted:
        if formatted[column].dtype == "object":
            formatted[column] = formatted[column].map(
                lambda value: (
                    value.replace("%", r"\%")
                    if isinstance(value, str) and "$" in value
                    else (
                        value.replace("%", r"\%").replace("_", r"\_")
                        if isinstance(value, str)
                        else value
                    )
                )
            )
    return formatted.to_latex(
        index=False,
        escape=False,
        column_format=column_format,
        float_format=lambda x: f"{x:.2f}",
    )


def write_table(frame, path, caption, label, column_format=None):
    path.write_text(
        "\\begin{table}[!htbp]\n\\centering\n\\small\n\\caption{"
        + caption
        + "}\n\\label{"
        + label
        + "}\n"
        + format_tabular(frame, column_format)
        + "\\end{table}\n",
        encoding="utf8",
    )


def write_table_fragment(frame, path):
    path.write_text(format_tabular(frame), encoding="utf8")


def write_panel_table(path, caption, label, panels):
    body = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\small",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
    ]
    for heading, content in panels:
        body.extend([f"\\textit{{{heading}}}", content, "\\vspace{0.8em}"])
    body.append("\\end{table}")
    path.write_text("\n".join(body) + "\n", encoding="utf8")


def survival_curve(audit):
    return kaplan_meier(
        audit.rename(columns={"survival_duration_months": "time_months"})[
            ["time_months", "event"]
        ]
    )


def build_working_bundle(root, output_dir):
    results_dir = root / "results"
    diagnostics_dir = results_dir / "diagnostics"
    extension_dir = results_dir / "extension"
    country_run_dir = results_dir / "country_replication_B1000"
    output_dir.mkdir(parents=True, exist_ok=True)
    # Remove names superseded by the consolidated appendix objects on reruns.
    for stale in [
        "figure_A1_transition_14.pdf",
        "figure_A1_transition_17.pdf",
        "figure_A3_endpoint_displacement.pdf",
        "figure_A3_endpoint_displacement.png",
        "figure_A3_endpoint_displacement_source.csv",
        "table_A2_displacement_granularity.csv",
        "table_A2_displacement_granularity.tex",
        "table_A2_panel_A_full.csv",
        "table_A2_panel_A_full.tex",
        "table_A2_panel_B_common.csv",
        "table_A2_panel_B_common.tex",
        "table_A2_panel_C_30industry.csv",
        "table_A2_panel_C_30industry.tex",
        "table_A3_method_diagnostics.csv",
        "table_A3_method_diagnostics.tex",
        "table_A4_bootstrap_audit.csv",
        "table_A4_bootstrap_audit.tex",
        "table_A1_panel_A_specification_sensitivity.tex",
        "table_A1_panel_B_materiality_thresholds.tex",
        "table_A2_panel_A_common_origin.tex",
        "table_A2_panel_B_30industry.tex",
        "table_A3_panel_A_us_industries.tex",
        "table_A3_panel_B_countries.tex",
        "table_A4_panel_A_endpoint_inference.tex",
        "table_A4_panel_B_country_secondary.tex",
        "table_A4_panel_C_primary_displacement_intervals.tex",
        "table_A5_panel_A_methods.tex",
        "table_A5_panel_B_data.tex",
    ]:
        (output_dir / stale).unlink(missing_ok=True)
    primary_summary = json.loads(
        (results_dir / "primary_17_definitive_B2000/summary.json").read_text()
    )
    primary_intervals_saved = json.loads(
        (
            results_dir / "primary_17_definitive_B2000/outer_bootstrap_intervals.json"
        ).read_text()
    )
    country_summary = json.loads((country_run_dir / "summary.json").read_text())
    country_intervals = json.loads(
        (country_run_dir / "outer_bootstrap_intervals.json").read_text()
    )
    endpoint_table = pd.DataFrame(
        [
            ["Endpoint pairs", 84, 36],
            [
                "Mean endpoint loss (bp)",
                f'{to_basis_points(primary_summary["mean_endpoint_loss"]):.2f}',
                f'{to_basis_points(country_summary["mean_endpoint_loss"]):.2f}',
            ],
            [
                "95% bootstrap CI (bp)",
                f'[{to_basis_points(primary_intervals_saved["baseline_mean_endpoint_loss"][0]):.2f}, {to_basis_points(primary_intervals_saved["baseline_mean_endpoint_loss"][1]):.2f}]',
                f'[{to_basis_points(country_intervals["mean_endpoint_loss"][0]):.2f}, {to_basis_points(country_intervals["mean_endpoint_loss"][1]):.2f}]',
            ],
            ["Median (bp)", "0.00", "0.00"],
            [
                "P75 (bp)",
                f'{to_basis_points(primary_summary["p75_endpoint_loss"]):.2f}',
                f'{to_basis_points(country_summary["p75_endpoint_loss"]):.2f}',
            ],
            [
                "P90 (bp)",
                f'{to_basis_points(primary_summary["p90_endpoint_loss"]):.2f}',
                f'{to_basis_points(country_summary["p90_endpoint_loss"]):.2f}',
            ],
            [
                "Literal switching",
                f'{to_percent(primary_summary["literal_switch_frequency"]):.1f}%',
                f'{to_percent(country_summary["literal_switch_frequency"]):.1f}%',
            ],
        ],
        columns=["Metric", "17 U.S. industries", "14 developed-country markets"],
    )
    endpoint_table.to_csv(output_dir / "table_1.csv", index=False)
    write_table(
        endpoint_table,
        output_dir / "table_1.tex",
        "Endpoint reproducibility",
        "tab:endpoint",
        "lcc",
    )
    math_ci = lambda a, b: f"$[{to_basis_points(a):.2f},\\,{to_basis_points(b):.2f}]$"
    math_num = lambda x: f"${to_basis_points(x):+.2f}$"
    selector_table = pd.DataFrame(
        [
            ["Decision dates", 75, 27],
            [
                "Selector hit rate",
                f'{to_percent(primary_summary["selector_hit_rate"]):.1f}%',
                f'{to_percent(country_summary["selector_hit_rate"]):.1f}%',
            ],
            [
                "Selection regret (bp)",
                math_num(primary_summary["mean_selection_regret"]),
                math_num(country_summary["mean_selection_regret"]),
            ],
            [
                r"\quad 95% CI",
                math_ci(*primary_intervals_saved["baseline_mean_selection_regret"]),
                math_ci(*country_intervals["mean_selection_regret"]),
            ],
            [
                "Selector minus ensemble (bp)",
                math_num(primary_summary["mean_selector_minus_ensemble"]),
                math_num(country_summary["mean_selector_minus_ensemble"]),
            ],
            [
                r"\quad 95% CI",
                math_ci(
                    *primary_intervals_saved["baseline_mean_selector_minus_ensemble"]
                ),
                math_ci(*country_intervals["mean_selector_minus_ensemble"]),
            ],
        ],
        columns=["Metric", "17 U.S. industries", "14 developed-country markets"],
    )
    selector_table.to_csv(output_dir / "table_2.csv", index=False)
    write_table(
        selector_table,
        output_dir / "table_2.tex",
        "Ex-ante recoverability",
        "tab:recoverability",
        "lcc",
    )
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.18, top=0.80, wspace=0.035)
    specs = [
        (
            "17 industries",
            diagnostics_dir / "survival_origin_audit_17_baseline.csv",
            diagnostics_dir / "material_origin_audit_17_baseline.csv",
        ),
        (
            "14 countries",
            extension_dir / "countries_literal_origin_audit.csv",
            extension_dir / "countries_material25_origin_audit.csv",
        ),
    ]
    handles = []
    for ax, (title, literal_path, material_path) in zip(axes, specs):
        for label, path in [
            ("Literal", literal_path),
            ("Material >25 bp", material_path),
        ]:
            frame = survival_curve(pd.read_csv(path))
            line = ax.step(
                [0, *frame.time_months],
                [1, *frame.survival],
                where="post",
                label="Material (>25 bp)" if label.startswith("Material") else label,
            )
            handles.extend(line if not handles else [])
        ax.set_title(title)
        ax.set(
            xlabel="Months since initial terminal date", xlim=(0, 150), ylim=(0, 1.02)
        )
    axes[0].set_ylabel("Kaplan--Meier survival probability")
    legend_handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=2,
        frameon=False,
    )
    fig.savefig(output_dir / "figure_1_winner_durability.pdf")
    fig.savefig(output_dir / "figure_1_winner_durability.png", dpi=220)
    plt.close(fig)
    # Lean appendix objects.
    sensitivity = pd.read_csv(extension_dir / "primary17_gamma_cost_sensitivity.csv")
    materiality = pd.read_csv(extension_dir / "materiality_threshold_sensitivity.csv")
    extra = []
    for run_name, label in [
        ("primary_17_L36", "L=36"),
        ("primary_17_L120", "L=120"),
        ("primary_17_quarterly", "Quarterly"),
    ]:
        summary = json.loads((results_dir / run_name / "summary.json").read_text())
        extra.append(
            {
                "setting": label,
                "mean_endpoint_loss": summary["mean_endpoint_loss"],
                "literal_switch_frequency": summary["literal_switch_frequency"],
                "loss_exceeds_25bp_frequency": float("nan"),
                "survival_12_complete_followup": summary["survival_12_months"],
                "median_survival_months_full_km": summary["median_survival_months"],
            }
        )
    sensitivity = pd.concat([pd.DataFrame(extra), sensitivity], ignore_index=True)
    sens_by = sensitivity.set_index("setting")

    def sens_row(key, label):
        summary = sens_by.loc[key]
        return [
            label,
            f"{10000*summary.mean_endpoint_loss:.2f}",
            f"{100*summary.literal_switch_frequency:.1f}%",
            int(summary.median_survival_months_full_km),
        ]

    baseline = [
        "Baseline: L=60 months",
        f'{to_basis_points(primary_summary["mean_endpoint_loss"]):.2f}',
        f'{to_percent(primary_summary["literal_switch_frequency"]):.1f}%',
        int(primary_summary["median_survival_months"]),
    ]
    a1a = pd.DataFrame(
        [
            sens_row("L=36", "L=36 months"),
            baseline,
            sens_row("L=120", "L=120 months"),
            sens_row("Quarterly", "Quarterly rebalancing"),
            sens_row("gamma2", r"$\gamma=2$"),
            [
                r"Baseline: $\gamma=5$",
                f'{to_basis_points(primary_summary["mean_endpoint_loss"]):.2f}',
                f'{to_percent(primary_summary["literal_switch_frequency"]):.1f}%',
                int(primary_summary["median_survival_months"]),
            ],
            sens_row("gamma10", r"$\gamma=10$"),
            sens_row("cost0", "c=0 bp"),
            [
                "Baseline: c=25 bp",
                f'{to_basis_points(primary_summary["mean_endpoint_loss"]):.2f}',
                f'{to_percent(primary_summary["literal_switch_frequency"]):.1f}%',
                int(primary_summary["median_survival_months"]),
            ],
            sens_row("cost50", "c=50 bp"),
        ],
        columns=[
            "Setting",
            "Mean endpoint loss (bp)",
            "Literal switching",
            "Median literal survival (months)",
        ],
    )
    a1b = materiality[
        [
            "universe",
            "threshold_bp",
            "survival_12_complete_followup",
            "survival_24_complete_followup",
            "median_survival_months_full_km",
        ]
    ].copy()
    a1b["universe"] = a1b["universe"].replace(
        {"primary17": "17 U.S. industries", "countries": "14 developed-country markets"}
    )
    a1b["survival_12_complete_followup"] = a1b["survival_12_complete_followup"].map(
        lambda x: f"{100*x:.1f}%"
    )
    a1b["survival_24_complete_followup"] = a1b["survival_24_complete_followup"].map(
        lambda x: f"{100*x:.1f}%"
    )
    a1b["median_survival_months_full_km"] = a1b[
        "median_survival_months_full_km"
    ].astype(int)
    a1b.columns = [
        "Universe",
        r"Threshold $\delta$ (bp)",
        r"$S(12)$",
        r"$S(24)$",
        "Median (months)",
    ]
    a1a.to_csv(
        output_dir / "table_A1_panel_A_specification_sensitivity.csv", index=False
    )
    a1b.to_csv(output_dir / "table_A1_panel_B_materiality_thresholds.csv", index=False)
    a1a_tex = (
        format_tabular(a1a)
        .replace(
            "\\midrule\n",
            "\\midrule\n\\multicolumn{4}{l}{\\textit{Estimation and rebalancing}} \\\\\n",
            1,
        )
        .replace(
            "$\\gamma=2$ &",
            "\\multicolumn{4}{l}{\\textit{Risk aversion}} \\\\\n$\\gamma=2$ &",
        )
        .replace(
            "c=0 bp &",
            "\\multicolumn{4}{l}{\\textit{Transaction costs}} \\\\\nc=0 bp &",
        )
    )
    write_panel_table(
        output_dir / "table_A1.tex",
        "Robustness to specification choices",
        "tab:robustness",
        [
            ("Panel A. Implementation and preference sensitivity", a1a_tex),
            ("Panel B. Economic-materiality threshold", format_tabular(a1b)),
        ],
    )
    displacement = pd.concat(
        [
            pd.read_csv(extension_dir / "primary17_displacement.csv").assign(
                universe="17 U.S. industries"
            ),
            pd.read_csv(extension_dir / "countries_displacement.csv").assign(
                universe="14 developed-country markets"
            ),
        ]
    ).copy()
    for col in [
        "mean_endpoint_loss",
        "median_endpoint_loss",
        "p75_endpoint_loss",
        "p90_endpoint_loss",
    ]:
        displacement[col] *= 10000
    for col in ["literal_switch_frequency", "loss_exceeds_25bp_frequency"]:
        displacement[col] *= 100
    displacement = displacement[
        [
            "universe",
            "h",
            "sample",
            "mean_endpoint_loss",
            "p90_endpoint_loss",
            "literal_switch_frequency",
            "loss_exceeds_25bp_frequency",
            "n_origins",
        ]
    ]
    displacement.columns = [
        "Universe",
        "h (months)",
        "Sample",
        "Mean loss (bp)",
        "P90 (bp)",
        "Switching (%)",
        "Loss >25 bp (%)",
        "n",
    ]
    displacement.to_csv(output_dir / "source_A2_displacement_all.csv", index=False)
    # Figure 2: common-terminal-date displacement shares. It is descriptive;
    # endpoint-loss levels and their primary bootstrap intervals remain in A4.
    figure2_mean_loss = displacement.loc[
        displacement["Sample"] == "full_eligible",
        ["Universe", "h (months)", "Mean loss (bp)"],
    ].copy()
    figure2 = displacement.loc[
        displacement["Sample"] == "common_calendar_origins",
        ["Universe", "h (months)", "Switching (%)", "Loss >25 bp (%)", "n"],
    ].copy()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    fig.subplots_adjust(left=0.09, right=0.99, bottom=0.19, top=0.78, wspace=0.035)
    titles = {
        "17 U.S. industries": "17 industries",
        "14 developed-country markets": "14 countries",
    }
    for ax, (universe, group) in zip(axes, figure2.groupby("Universe", sort=False)):
        group = group.sort_values("h (months)")
        ax.plot(
            group["h (months)"],
            group["Switching (%)"],
            marker="o",
            linewidth=2,
            label="Literal winner change",
        )
        ax.plot(
            group["h (months)"],
            group["Loss >25 bp (%)"],
            marker="o",
            linewidth=2,
            label="Material loss (>25 bp)",
        )
        ax.set(
            title=titles[universe],
            xlabel="Terminal-date displacement (months)",
            xticks=[6, 12, 24],
        )
    axes[0].set_ylabel("Share of terminal dates (%)")
    legend_handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=2,
        frameon=False,
    )
    fig.savefig(output_dir / "figure_2_endpoint_displacement.pdf")
    fig.savefig(output_dir / "figure_2_endpoint_displacement.png", dpi=220)
    plt.close(fig)
    figure2.to_csv(
        output_dir / "figure_2_endpoint_displacement_source.csv", index=False
    )
    # Retain the paired primary horizon intervals as an inference table, not
    # unequal visual ornamentation on the two-universe descriptive profile.
    primary_draws = pd.read_csv(
        results_dir / "primary_17_definitive_B2000/outer_bootstrap.csv"
    )
    primary_columns = {
        6: "h6_mean_endpoint_loss",
        12: "baseline_mean_endpoint_loss",
        24: "h24_mean_endpoint_loss",
    }
    primary_intervals = {
        h: (
            10000 * primary_draws[column].quantile(0.025),
            10000 * primary_draws[column].quantile(0.975),
        )
        for h, column in primary_columns.items()
    }
    q_common = (
        displacement.loc[displacement.Sample == "common_calendar_origins"]
        .drop(columns="Sample")
        .copy()
    )
    q_common["Universe"] = (
        q_common["Universe"] + " (n=" + q_common["n"].astype(int).astype(str) + ")"
    )
    q_common = q_common.drop(columns="n")
    q_common[["Switching (%)", "Loss >25 bp (%)"]] = q_common[
        ["Switching (%)", "Loss >25 bp (%)"]
    ].map(lambda x: f"{x:.1f}%")
    q_common.columns = [
        "Universe",
        "h (months)",
        "Mean loss (bp)",
        "P90 (bp)",
        "Switching",
        "Loss >25 bp",
    ]
    q_common.loc[q_common.duplicated("Universe"), "Universe"] = ""
    q_common.to_csv(output_dir / "table_A2_panel_A_common_origin.csv", index=False)
    s30 = json.loads((results_dir / "replication_30_B1000/summary.json").read_text())
    i30 = json.loads(
        (
            results_dir / "replication_30_B1000/outer_bootstrap_intervals.json"
        ).read_text()
    )
    q30 = pd.DataFrame(
        [
            [
                "30 U.S. industries",
                f'{to_basis_points(s30["mean_endpoint_loss"]):.2f}',
                f'[{to_basis_points(i30["mean_endpoint_loss"][0]):.2f}, {to_basis_points(i30["mean_endpoint_loss"][1]):.2f}]',
                f'{to_percent(s30["literal_switch_frequency"]):.1f}%',
                s30["median_survival_months"],
            ]
        ]
    )
    q30.columns = [
        "Universe",
        "Mean loss (bp)",
        "95% CI (bp)",
        "Switching",
        "Literal median (months)",
    ]
    q30["Literal median (months)"] = q30["Literal median (months)"].astype(int)
    q30.to_csv(output_dir / "table_A2_panel_B_30industry.csv", index=False)
    write_panel_table(
        output_dir / "table_A2.tex",
        "Additional robustness across horizons and universes",
        "tab:additional-robustness",
        [
            (
                "Panel A. Common-origin endpoint-displacement robustness",
                format_tabular(q_common),
            ),
            ("Panel B. 30-industry granularity check", format_tabular(q30)),
        ],
    )
    labels = {
        "equal_weight": "Equal weight",
        "sample_gmv": "Sample GMV",
        "ledoit_wolf_gmv": "Ledoit--Wolf GMV",
        "inverse_volatility": "Inverse volatility",
        "erc": "ERC",
    }
    frames = []
    for universe, file in [
        ("17 U.S. industries", "primary17_winner_conditioned.csv"),
        ("14 developed-country markets", "countries_winner_conditioned.csv"),
    ]:
        frame = (
            pd.read_csv(extension_dir / file)
            .set_index("original_winner")
            .reindex(labels)
            .reset_index()
        )
        frame["universe"] = universe
        frames.append(frame)
    a3 = pd.concat(frames)
    a3["original_winner"] = a3.original_winner.map(labels)
    a3["switches"] = a3.apply(
        lambda x: (
            f"{round(x.switch_frequency*x.n_origins):.0f}/{x.n_origins:.0f}"
            if pd.notna(x.n_origins)
            else "--"
        ),
        axis=1,
    )
    a3["material_events"] = a3.apply(
        lambda x: (
            f"{round(x.loss_exceeds_25bp*x.n_origins):.0f}/{x.n_origins:.0f}"
            if pd.notna(x.n_origins)
            else "--"
        ),
        axis=1,
    )
    a3["mean_loss_publication"] = a3.apply(
        lambda x: (
            f"{10000*x.mean_endpoint_loss:.2f}"
            if pd.notna(x.n_origins) and x.n_origins >= 5
            else "--"
        ),
        axis=1,
    )
    a3["n_origins"] = a3["n_origins"].map(
        lambda x: str(int(x)) if pd.notna(x) else "--"
    )
    a3 = a3[
        [
            "original_winner",
            "n_origins",
            "switches",
            "mean_loss_publication",
            "material_events",
            "universe",
        ]
    ].fillna("--")
    a3.columns = [
        "Initial winner",
        "Origins",
        "Switches",
        "Mean endpoint loss (bp)",
        "Loss >25 bp",
        "Universe",
    ]
    a3.to_csv(output_dir / "source_A3_method_diagnostics_all.csv", index=False)
    a3_us = a3.loc[a3["Universe"] == "17 U.S. industries"].drop(columns="Universe")
    a3_country = a3.loc[a3["Universe"] == "14 developed-country markets"].drop(
        columns="Universe"
    )
    write_panel_table(
        output_dir / "table_A3.tex",
        "Method-conditioned diagnostics. Conditional mean endpoint loss is suppressed when fewer than five eligible origins are available; event counts remain reported.",
        "tab:methods",
        [
            ("Panel A. 17 U.S. industries", format_tabular(a3_us)),
            ("Panel B. 14 developed-country markets", format_tabular(a3_country)),
        ],
    )
    leave_one_out = pd.concat(
        [
            pd.read_csv(extension_dir / "primary17_leave_one_out.csv").assign(
                universe="17 industries"
            ),
            pd.read_csv(extension_dir / "countries_leave_one_out.csv").assign(
                universe="countries"
            ),
        ]
    )
    full_losses = {
        "17 industries": primary_summary["mean_endpoint_loss"],
        "countries": country_summary["mean_endpoint_loss"],
    }
    leave_one_out["influence_shift_bp"] = leave_one_out.apply(
        lambda x: 10000 * (x["mean_endpoint_loss"] - full_losses[x["universe"]]), axis=1
    )
    loo_labels = {
        "Clths": "Apparel",
        "Durbl": "Durables",
        "Chems": "Chemicals",
        "Cnsum": "Consumer goods",
        "Cnstr": "Construction",
        "FabPr": "Fabricated products",
        "Machn": "Machinery",
        "Trans": "Transport",
        "Utils": "Utilities",
        "Rtail": "Retail",
        "Finan": "Finance",
    }
    leave_one_out["display_asset"] = leave_one_out.omitted_asset.replace(loo_labels)
    leave_one_out.to_csv(output_dir / "figure_A2_leave_one_out_source.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5), constrained_layout=True)
    for ax, (universe, group) in zip(
        axes, leave_one_out.groupby("universe", sort=False)
    ):
        group = group.sort_values("influence_shift_bp", ascending=False).reset_index(
            drop=True
        )
        ax.plot(group.influence_shift_bp, range(len(group)), "o")
        ax.axvline(0, ls="--", color="black")
        ax.set(
            title="17 industries" if universe == "17 industries" else "14 countries",
            yticks=range(len(group)),
            yticklabels=group.display_asset,
            xlabel="Change in mean endpoint loss (bp)",
        )
        ax.invert_yaxis()
    fig.savefig(output_dir / "figure_A2_leave_one_out.pdf")
    fig.savefig(output_dir / "figure_A2_leave_one_out.png", dpi=220)
    plt.close(fig)
    # A4 panel A: endpoint inference under each resampling law.
    bootstrap_rows = []
    for name, design, folder, reps, key in [
        (
            "17 U.S. industries",
            "Stationary bootstrap",
            "primary_17_definitive_B2000",
            2000,
            "baseline_mean_endpoint_loss",
        ),
        (
            "17 U.S. industries",
            "Fixed circular blocks (12 months)",
            "primary_17_fixedblock12_B1000",
            1000,
            "mean_endpoint_loss",
        ),
        (
            "17 U.S. industries",
            "Fixed circular blocks (24 months)",
            "primary_17_fixedblock24_B1000",
            1000,
            "mean_endpoint_loss",
        ),
        (
            "14 developed-country markets",
            "Stationary bootstrap",
            "country_replication_B1000",
            1000,
            "mean_endpoint_loss",
        ),
    ]:
        summary = json.loads((results_dir / folder / "summary.json").read_text())
        interval = json.loads(
            (results_dir / folder / "outer_bootstrap_intervals.json").read_text()
        )[key]
        bootstrap_rows.append(
            [
                name,
                design,
                reps,
                to_basis_points(summary["mean_endpoint_loss"]),
                f"[{to_basis_points(interval[0]):.2f}, {to_basis_points(interval[1]):.2f}]",
            ]
        )
    a4a = pd.DataFrame(
        bootstrap_rows,
        columns=[
            "Universe",
            "Bootstrap design",
            "B",
            "Endpoint loss (bp)",
            "95% CI (bp)",
        ],
    ).round(2)
    a4a["Bootstrap design"] = a4a["Bootstrap design"].replace(
        {
            "Stationary bootstrap": "Stationary",
            "Fixed circular blocks (12 months)": "Circular block, 12m",
            "Fixed circular blocks (24 months)": "Circular block, 24m",
        }
    )
    a4a.to_csv(output_dir / "table_A4_panel_A_endpoint_inference.csv", index=False)
    a4b = pd.read_csv(extension_dir / "country_bootstrap_B1000_summary.csv")[
        [
            "metric",
            "point_estimate",
            "ci_low",
            "ci_high",
            "unit",
            "bootstrap_replications",
        ]
    ].copy()
    a4b["Estimate"] = a4b.apply(
        lambda x: (
            f"{x.point_estimate:.1f}%" if x.unit == "%" else f"{x.point_estimate:.2f}"
        ),
        axis=1,
    )
    a4b["95% CI"] = a4b.apply(
        lambda x: (
            f"[{x.ci_low:.1f}%, {x.ci_high:.1f}%]"
            if x.unit == "%"
            else f"[{x.ci_low:.2f}, {x.ci_high:.2f}]"
        ),
        axis=1,
    )
    a4b["metric"] = a4b.apply(
        lambda x: f"{x.metric} (%)" if x.unit == "%" else x.metric, axis=1
    )
    a4b = a4b[["metric", "Estimate", "95% CI"]]
    a4b.columns = ["Country statistic", "Estimate", "95% CI"]
    a4b.to_csv(output_dir / "table_A4_panel_B_country_secondary.csv", index=False)
    a4c = pd.DataFrame(
        [
            [
                h,
                figure2_mean_loss.loc[
                    (figure2_mean_loss["Universe"] == "17 U.S. industries")
                    & (figure2_mean_loss["h (months)"] == h),
                    "Mean loss (bp)",
                ].iloc[0],
                f"[{low:.2f}, {high:.2f}]",
            ]
            for h, (low, high) in primary_intervals.items()
        ],
        columns=["Displacement (months)", "Endpoint loss (CEQ bp)", "95% CI (bp)"],
    ).round(2)
    a4c.to_csv(
        output_dir / "table_A4_panel_C_primary_displacement_intervals.csv", index=False
    )
    write_panel_table(
        output_dir / "table_A4.tex",
        "Bootstrap inference audit",
        "tab:bootstrap",
        [
            ("Panel A. Endpoint-loss inference", format_tabular(a4a)),
            (
                "Panel B. Primary-universe endpoint-displacement inference",
                format_tabular(a4c),
            ),
            (
                "Panel C. Country secondary outcomes (all intervals use B=1,000 stationary-bootstrap replications)",
                format_tabular(a4b),
            ),
        ],
    )
    # Figure A1: two transition matrices, directly comparable on a 0--100 scale.
    matrices = []
    for name, file, winner_file in [
        (
            "17 industries",
            extension_dir / "primary17_transition_row_percent.csv",
            extension_dir / "primary17_winner_conditioned.csv",
        ),
        (
            "14 countries",
            extension_dir / "countries_transition_row_percent.csv",
            extension_dir / "countries_winner_conditioned.csv",
        ),
    ]:
        frame = pd.read_csv(file, index_col=0).reindex(index=labels, columns=labels)
        counts = (
            pd.read_csv(winner_file)
            .set_index("original_winner")["n_origins"]
            .reindex(labels)
            .fillna(0)
            .astype(int)
        )
        matrices.append((name, frame, counts))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
    for ax, (name, frame, counts) in zip(axes, matrices):
        values = frame.fillna(0).to_numpy() * 100
        image = ax.imshow(values, vmin=0, vmax=100, cmap="Blues")
        for i in range(5):
            for j in range(5):
                cell = "--" if pd.isna(frame.iloc[i, j]) else f"{values[i,j]:.0f}"
                ax.text(
                    j,
                    i,
                    cell,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if values[i, j] >= 55 else "black",
                )
        ax.set(
            title=name,
            xticks=range(5),
            xticklabels=[labels[x] for x in frame.columns],
            yticks=range(5),
            yticklabels=[f"{labels[x]} (n={counts[x]})" for x in frame.index],
            xlabel="Winner after 12 months",
            ylabel="Initial winner",
        )
        plt.setp(ax.get_xticklabels(), rotation=38, ha="right")
    fig.colorbar(image, ax=axes, label="Row percentage", shrink=0.85)
    fig.savefig(output_dir / "figure_A1_transition_matrices.pdf")
    fig.savefig(output_dir / "figure_A1_transition_matrices.png", dpi=220)
    plt.close(fig)
    methods = pd.DataFrame(
        [
            ["Equal weight", "None", r"$w_i=1/N$"],
            ["Sample GMV", "Sample covariance", "Long-only minimum variance"],
            ["Ledoit--Wolf GMV", "Shrinkage covariance", "Long-only minimum variance"],
            ["Inverse volatility", "Sample volatility", r"$w_i\propto1/\hat\sigma_i$"],
            ["ERC", "Sample covariance", "Equal risk contributions"],
        ],
        columns=["Method", "Risk input", "Allocation rule"],
    )
    datasets = pd.DataFrame(
        [
            [
                "17 U.S. industries (N=17)",
                "Kenneth French Data Library",
                "1926-07--2026-07",
                "1931-07",
                84,
                75,
            ],
            [
                "14 developed-country markets (N=14)",
                "Kenneth French international",
                "1975-01--2025-12",
                "1980-01",
                36,
                27,
            ],
            [
                "30 U.S. industries (N=30)",
                "Kenneth French Data Library",
                "1926-07--2026-07",
                "1931-07",
                84,
                75,
            ],
        ],
        columns=[
            "Universe",
            "Source",
            "Sample",
            "OOS start",
            "Endpoint pairs",
            "Ex-ante dates",
        ],
    )
    methods.to_csv(output_dir / "table_A5_panel_A_methods.csv", index=False)
    datasets.to_csv(output_dir / "table_A5_panel_B_data.csv", index=False)
    write_panel_table(
        output_dir / "table_A5.tex",
        "Portfolio methods and sample construction. All methods are long-only and fully invested, use a 60-month estimation window, and rebalance monthly. Returns are monthly USD total returns; the country universe satisfies the frozen January-1975 balanced-panel rule.",
        "tab:implementation-data",
        [
            ("Panel A. Portfolio methods", format_tabular(methods)),
            ("Panel B. Data and analysis samples", format_tabular(datasets)),
        ],
    )
    (output_dir / "README.md").write_text(
        "# Lean FRL bundle\n\nMain text: Table 1, Figure 1 (Kaplan--Meier winner durability), Figure 2 (terminal-date displacement), and Table 2. For the appendix, insert only `table_A1.tex` through `table_A5.tex`: these are the five publication-level floats, with their panels already inlined. CSV files remain as reproducibility sources. Appendix Table A4 includes the primary h=6/12/24 bootstrap intervals.\n",
        encoding="utf8",
    )
    (output_dir / "FIGURE_NOTES.md").write_text(
        "# Figure captions and notes\n\n## Figure 1. Winner durability\n\nKaplan--Meier survival of the method identified as winner at each December origin. Literal failure occurs at the first subsequent monthly endpoint at which the original winner loses first place; material failure occurs when its CEQ shortfall first exceeds 25 annualized bp. Recovery of first place does not reset failure.\n\n## Figure 2. Terminal-date displacement\n\nShares of the common eligible terminal dates with a literal winner change or a material endpoint loss at the prespecified 6-, 12-, and 24-month terminal-date displacements. Lines connect reported design points for visual guidance only; no functional form or monotonic relationship is estimated.\n\n## Figure A1. Winner transitions\n\nRows are conditioned on the method winning at the initial endpoint. Sparse rows are descriptive; in the country universe, inverse volatility and ERC each occur as the initial winner once.\n\n## Figure A2. Leave-one-out sensitivity of mean endpoint loss\n\nEach point is the change in mean 12-month endpoint loss after excluding the indicated asset relative to the corresponding full-universe estimate. The dashed line denotes no change. Asset omission changes both the opportunity set and its dimension, so differences are sensitivity diagnostics rather than asset-specific causal contributions.\n",
        encoding="utf8",
    )


def main():
    from .final_publication import main as final_main

    final_main()


if __name__ == "__main__":
    main()
