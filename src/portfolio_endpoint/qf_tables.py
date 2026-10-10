"""Publication appendix table bodies from frozen saved outputs only."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from .analysis import TIE_BREAK_ORDER


def replace_table_bodies(template: str, bodies: list[str]) -> str:
    """Replace every data body, preserving layout headers and notes."""
    iterator = iter(bodies)
    count = len(re.findall(r"\\midrule\s*.*?\\bottomrule", template, re.S))
    if count != len(bodies):
        raise ValueError(f"Layout mismatch: {count} bodies versus {len(bodies)}")
    return re.sub(
        r"(\\midrule\s*).*?(\\bottomrule)",
        lambda match: match[1] + next(iterator) + "\n" + match[2],
        template,
        flags=re.S,
    )


def format_table_rows(values: list[list]) -> str:
    return "\n".join(" & ".join(map(str, row)) + r" \\" for row in values)


def format_percentage(value: float) -> str:
    """Format a native proportion, rounding only at the display step."""
    return f"{100 * value:.1f}" + r"\%"


def format_basis_points(value: float) -> str:
    """Convert and format a native-unit return in basis points."""
    return f"{10000 * value:.2f}"


def format_interval_cell(point: float, interval, scale=10000, signed=False) -> str:
    fmt = "+.2f" if signed else ".2f"
    if scale == 100:
        estimate = format_percentage(point)
        lower, upper = [format_percentage(v) for v in interval]
    else:
        estimate = "$" + format(scale * point, fmt) + "$"
        lower, upper = [f"{scale * v:.2f}" for v in interval]
    return r"\makecell{" + estimate + r"\\\footnotesize$(" + lower + r",\," + upper + r")$}"


def appendix_tables(root: Path) -> tuple[dict[str, list[str]], dict]:
    results = root / "results"
    sources = {}

    def load_saved_run(folder):
        run = results / folder
        sources[folder] = [
            str(p.relative_to(root))
            for p in (
                run / "summary.json",
                run / "endpoint_pairs.csv",
                run / "ex_ante_selection.csv",
                run / "outer_bootstrap.csv",
            )
            if p.exists()
        ]
        summary = json.loads((run / "summary.json").read_text())
        pairs = pd.read_csv(run / "endpoint_pairs.csv")
        selection = pd.read_csv(run / "ex_ante_selection.csv")
        return summary, pairs, selection

    primary_summary, primary_endpoints, primary_selections = load_saved_run(
        "primary_17_definitive_B2000"
    )
    country_summary, country_endpoints, country_selections = load_saved_run(
        "country_replication_B1000"
    )
    granularity_summary, granularity_endpoints, granularity_selections = load_saved_run(
        "replication_30_B1000"
    )

    def saved_interval(folder, column):
        # Quantiles are recomputed from existing draws, not a new bootstrap.
        draws = pd.read_csv(results / folder / "outer_bootstrap.csv", usecols=[column])
        return draws[column].quantile([0.025, 0.975]).to_numpy()

    primary_intervals = {
        name: saved_interval("primary_17_definitive_B2000", "baseline_" + name)
        for name in (
            "mean_endpoint_loss",
            "mean_selection_regret",
            "mean_selector_minus_ensemble",
        )
    }
    country_intervals = {
        name: saved_interval("country_replication_B1000", name)
        for name in (
            "mean_endpoint_loss",
            "mean_selection_regret",
            "mean_selector_minus_ensemble",
            "literal_switch_frequency",
            "survival_12_months",
            "survival_24_months",
            "selector_hit_rate",
        )
    }

    a1 = format_table_rows(
        [
            [
                r"\textbf{Baseline}",
                r"\textbf{" + format_basis_points(primary_summary["mean_endpoint_loss"]) + "}",
                r"\textbf{" + format_percentage(primary_summary["literal_switch_frequency"]) + "}",
                r"\textbf{" + str(int(primary_summary["median_survival_months"])) + "}",
            ]
        ]
    )
    a1 += (
        "\n"
        + r"\addlinespace"
        + "\n"
        + r"\multicolumn{4}{l}{\textbf{Estimation window and rebalancing}} \\"
        + "\n"
    )
    eligible = {"baseline": len(primary_endpoints)}
    for folder, label in [
        ("primary_17_L36", r"$L=36$ months"),
        ("primary_17_L120", r"$L=120$ months"),
        ("primary_17_quarterly", "Quarterly rebalancing"),
    ]:
        summary, pairs, _ = load_saved_run(folder)
        eligible[folder] = len(pairs)
        a1 += (
            format_table_rows(
                [
                    [
                        r"\quad " + label,
                        format_basis_points(summary["mean_endpoint_loss"]),
                        format_percentage(summary["literal_switch_frequency"]),
                        int(summary["median_survival_months"]),
                    ]
                ]
            )
            + "\n"
        )
    sensitivity = pd.read_csv(results / "extension/primary17_gamma_cost_sensitivity.csv").set_index(
        "setting"
    )
    for heading, keys in [
        ("Risk aversion", [("gamma2", r"$\gamma=2$"), ("gamma10", r"$\gamma=10$")]),
        ("Transaction costs", [("cost0", r"$c=0$ bp"), ("cost50", r"$c=50$ bp")]),
    ]:
        a1 += r"\addlinespace" + "\n" + r"\multicolumn{4}{l}{\textbf{" + heading + r"}} \\" + "\n"
        for key, label in keys:
            row = sensitivity.loc[key]
            a1 += (
                format_table_rows(
                    [
                        [
                            r"\quad " + label,
                            format_basis_points(row.mean_endpoint_loss),
                            format_percentage(row.literal_switch_frequency),
                            int(row.median_survival_months_full_km),
                        ]
                    ]
                )
                + "\n"
            )
    material = pd.read_csv(results / "extension/materiality_threshold_sensitivity.csv")
    a1b = ""
    for name, label in [("primary17", "17 industries"), ("countries", "14 countries")]:
        a1b += r"\multicolumn{5}{l}{\textbf{" + label + r"}} \\" + "\n"
        a1b += (
            format_table_rows(
                [
                    [
                        "",
                        int(r.threshold_bp),
                        format_percentage(r.survival_12_complete_followup),
                        format_percentage(r.survival_24_complete_followup),
                        int(r.median_survival_months_full_km),
                    ]
                    for r in material.loc[material.universe == name].itertuples()
                ]
            )
            + "\n"
        )
    a2a = ""
    displacement = {}
    for name, label in [("primary17", "17 industries"), ("countries", "14 countries")]:
        frame = pd.read_csv(results / "extension" / f"{name}_displacement.csv")
        displacement[name] = frame
        common = frame.loc[frame["sample"] == "common_calendar_origins"]
        a2a += (
            r"\multicolumn{5}{l}{\textbf{"
            + label
            + "} ($n="
            + str(int(common.n_origins.iloc[0]))
            + r"$)} \\"
            + "\n"
        )
        a2a += (
            format_table_rows(
                [
                    [
                        int(r.h),
                        format_percentage(r.literal_switch_frequency),
                        format_percentage(r.loss_exceeds_25bp_frequency),
                        format_basis_points(r.mean_endpoint_loss),
                        format_basis_points(r.p90_endpoint_loss),
                    ]
                    for r in common.itertuples()
                ]
            )
            + "\n"
        )
    a2b = format_table_rows(
        [
            [
                "17 industries",
                format_interval_cell(
                    primary_summary["mean_endpoint_loss"],
                    primary_intervals["mean_endpoint_loss"],
                ),
                format_percentage(primary_summary["literal_switch_frequency"]),
                int(primary_summary["median_survival_months"]),
            ],
            [
                "30 industries",
                format_interval_cell(
                    granularity_summary["mean_endpoint_loss"],
                    saved_interval("replication_30_B1000", "mean_endpoint_loss"),
                ),
                format_percentage(granularity_summary["literal_switch_frequency"]),
                int(granularity_summary["median_survival_months"]),
            ],
        ]
    )
    labels = [
        "Equal weight",
        "Sample GMV",
        "Ledoit--Wolf GMV",
        "Inverse volatility",
        "ERC",
    ]
    a4 = []
    for pairs in (primary_endpoints, country_endpoints):
        method_rows = []
        for method, label in zip(TIE_BREAK_ORDER, labels):
            selected = pairs.loc[pairs.earlier_winner == method]
            n = len(selected)
            method_rows.append(
                [
                    label,
                    n,
                    f"{int(selected.literal_switch.sum())}/{n}" if n else "---",
                    (format_basis_points(selected.endpoint_loss.mean()) if n >= 5 else "---"),
                    (f"{int((selected.endpoint_loss > .0025).sum())}/{n}" if n else "---"),
                ]
            )
        a4.append(format_table_rows(method_rows))
    bootstrap_endpoint_rows = []
    for label, scheme, folder, point, key in [
        (
            "17 industries",
            "Stationary",
            "primary_17_definitive_B2000",
            primary_summary,
            "baseline_mean_endpoint_loss",
        ),
        (
            "",
            "Circular block, 12 months",
            "primary_17_fixedblock12_B1000",
            primary_summary,
            "mean_endpoint_loss",
        ),
        (
            "",
            "Circular block, 24 months",
            "primary_17_fixedblock24_B1000",
            primary_summary,
            "mean_endpoint_loss",
        ),
        (
            "14 countries",
            "Stationary",
            "country_replication_B1000",
            country_summary,
            "mean_endpoint_loss",
        ),
    ]:
        draws = pd.read_csv(results / folder / "outer_bootstrap.csv", usecols=[key])
        bootstrap_endpoint_rows.append(
            [
                label,
                scheme,
                len(draws),
                format_interval_cell(
                    point["mean_endpoint_loss"], draws[key].quantile([0.025, 0.975])
                ),
            ]
        )
    bootstrap_selection_rows = []
    for h, key in [
        (6, "h6_mean_endpoint_loss"),
        (12, "baseline_mean_endpoint_loss"),
        (24, "h24_mean_endpoint_loss"),
    ]:
        point = (
            displacement["primary17"]
            .loc[
                (displacement["primary17"]["sample"] == "full_eligible")
                & (displacement["primary17"].h == h),
                "mean_endpoint_loss",
            ]
            .iloc[0]
        )
        bootstrap_selection_rows.append(
            [
                h,
                format_interval_cell(point, saved_interval("primary_17_definitive_B2000", key)),
            ]
        )
    bootstrap_comparison_rows = []
    for label, key, scale, signed in [
        ("Mean endpoint loss (bp)", "mean_endpoint_loss", 10000, False),
        ("Winner change", "literal_switch_frequency", 100, False),
        (r"Winner-change $\widehat S_{\mathrm{KM}}(12)$", "survival_12_months", 100, False),
        (r"Winner-change $\widehat S_{\mathrm{KM}}(24)$", "survival_24_months", 100, False),
        ("Correct selection rate", "selector_hit_rate", 100, False),
        ("Selection regret (bp)", "mean_selection_regret", 10000, False),
        (
            r"Mean selector $-$ ensemble CEQ (bp)",
            "mean_selector_minus_ensemble",
            10000,
            True,
        ),
    ]:
        bootstrap_comparison_rows.append(
            [
                label,
                format_interval_cell(country_summary[key], country_intervals[key], scale, signed),
            ]
        )
    specification_rows = format_table_rows(
        [
            ["Equal weight", "None", r"$w_i=1/N$"],
            ["Sample GMV", "Sample covariance", "Long-only minimum variance"],
            [
                "Ledoit--Wolf GMV",
                "Ledoit--Wolf covariance",
                "Long-only minimum variance",
            ],
            ["Inverse volatility", "Sample volatility", r"$w_i\propto1/\hat\sigma_i$"],
            ["ERC", "Sample covariance", "Equal risk contributions"],
        ]
    )
    sample_rows = []
    for label, filename, pairs, selections in [
        (
            "17 industries",
            "ff_17_industry_value_weighted_monthly.csv",
            primary_endpoints,
            primary_selections,
        ),
        (
            "14 countries",
            "ff_international_country_markets_usd_monthly.csv",
            country_endpoints,
            country_selections,
        ),
        (
            "30 industries",
            "ff_30_industry_value_weighted_monthly.csv",
            granularity_endpoints,
            granularity_selections,
        ),
    ]:
        panel = pd.read_csv(root / "data/processed" / filename, index_col="date", parse_dates=True)
        sample_rows.append(
            [
                label + f" ($N={panel.shape[1]}$)",
                panel.index[0].strftime("%Y-%m") + "--" + panel.index[-1].strftime("%Y-%m"),
                panel.index[60].strftime("%Y-%m"),
                len(pairs),
                len(selections),
            ]
        )
    return {
        "table_A1": [a1, a1b],
        "table_A2": [a2a, a2b],
        "table_A3": a4,
        "table_A4": [
            format_table_rows(bootstrap_endpoint_rows),
            format_table_rows(bootstrap_selection_rows),
            format_table_rows(bootstrap_comparison_rows),
        ],
        "table_A5": [specification_rows, format_table_rows(sample_rows)],
    }, {
        "canonical_runs": sources,
        "specification_pair_counts": eligible,
        "primary_h24_common_material_pct": 100
        * displacement["primary17"]
        .loc[
            (displacement["primary17"].h == 24)
            & (displacement["primary17"]["sample"] == "common_calendar_origins"),
            "loss_exceeds_25bp_frequency",
        ]
        .iloc[0],
    }
