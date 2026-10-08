"""Assemble the final six-table appendix from frozen results and layout templates.

Templates supply typography and prose, never numerical table cells. No analysis
or bootstrap runner is invoked. Original submitted and frozen files are read-only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

import pandas as pd

from .analysis import TIE_BREAK_ORDER
from .frl_publication import build_working_bundle
from .ingest import project_root, sha256


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
    return (
        r"\makecell{"
        + estimate
        + r"\\\footnotesize$("
        + lower
        + r",\,"
        + upper
        + r")$}"
    )


def final_tables(root: Path) -> tuple[dict[str, list[str]], dict]:
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

    def headline(pairs):
        changed = pairs.loc[pairs.literal_switch]
        return {
            "n": len(pairs),
            "switch_rate": pairs.literal_switch.sum() / len(pairs),
            "material_rate": (pairs.endpoint_loss > 0.0025).sum() / len(pairs),
            "mean": pairs.endpoint_loss.mean(),
            "switches": len(changed),
            "switch_mean": changed.endpoint_loss.mean(),
            "switch_median": changed.endpoint_loss.median(),
            "switch_material": (changed.endpoint_loss > 0.0025).sum() / len(changed),
        }

    primary_headline, country_headline = headline(primary_endpoints), headline(
        country_endpoints
    )
    t1 = (
        format_table_rows(
            [
                ["Endpoint pairs", primary_headline["n"], country_headline["n"]],
                [
                    "Literal winner change",
                    format_percentage(primary_headline["switch_rate"]),
                    format_percentage(country_headline["switch_rate"]),
                ],
                [
                    r"Material endpoint loss $>25$ bp",
                    format_percentage(primary_headline["material_rate"]),
                    format_percentage(country_headline["material_rate"]),
                ],
                [
                    "Mean endpoint loss (bp)",
                    format_interval_cell(
                        primary_headline["mean"],
                        primary_intervals["mean_endpoint_loss"],
                    ),
                    format_interval_cell(
                        country_headline["mean"],
                        country_intervals["mean_endpoint_loss"],
                    ),
                ],
            ]
        )
        + "\n"
        + r"\addlinespace[0.25em]"
        + "\n"
        + r"\multicolumn{3}{l}{\textbf{Conditional on a literal winner change}}\\[-0.15em]"
        + "\n"
        + format_table_rows(
            [
                [
                    r"\quad Number of switches",
                    primary_headline["switches"],
                    country_headline["switches"],
                ],
                [
                    r"\quad Mean endpoint loss (bp)",
                    format_basis_points(primary_headline["switch_mean"]),
                    format_basis_points(country_headline["switch_mean"]),
                ],
                [
                    r"\quad Median endpoint loss (bp)",
                    format_basis_points(primary_headline["switch_median"]),
                    format_basis_points(country_headline["switch_median"]),
                ],
                [
                    r"\quad Material endpoint loss $>25$ bp",
                    format_percentage(primary_headline["switch_material"]),
                    format_percentage(country_headline["switch_material"]),
                ],
            ]
        )
    )
    t2 = format_table_rows(
        [
            ["Decision dates", len(primary_selections), len(country_selections)],
            [
                "Correct selection rate",
                format_percentage(primary_selections.selector_hit.mean()),
                format_percentage(country_selections.selector_hit.mean()),
            ],
            [
                "Selection regret (bp)",
                format_interval_cell(
                    primary_selections.selection_regret.mean(),
                    primary_intervals["mean_selection_regret"],
                ),
                format_interval_cell(
                    country_selections.selection_regret.mean(),
                    country_intervals["mean_selection_regret"],
                ),
            ],
            [
                r"Selector $-$ ensemble CEQ (bp)",
                format_interval_cell(
                    primary_selections.selector_minus_ensemble.mean(),
                    primary_intervals["mean_selector_minus_ensemble"],
                    signed=True,
                ),
                format_interval_cell(
                    country_selections.selector_minus_ensemble.mean(),
                    country_intervals["mean_selector_minus_ensemble"],
                    signed=True,
                ),
            ],
        ]
    )
    a1 = format_table_rows(
        [
            [
                r"\textbf{Baseline}",
                r"\textbf{"
                + format_basis_points(primary_summary["mean_endpoint_loss"])
                + "}",
                r"\textbf{"
                + format_percentage(primary_summary["literal_switch_frequency"])
                + "}",
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
    sensitivity = pd.read_csv(
        results / "extension/primary17_gamma_cost_sensitivity.csv"
    ).set_index("setting")
    for heading, keys in [
        ("Risk aversion", [("gamma2", r"$\gamma=2$"), ("gamma10", r"$\gamma=10$")]),
        ("Transaction costs", [("cost0", r"$c=0$ bp"), ("cost50", r"$c=50$ bp")]),
    ]:
        a1 += (
            r"\addlinespace"
            + "\n"
            + r"\multicolumn{4}{l}{\textbf{"
            + heading
            + r"}} \\"
            + "\n"
        )
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
    near = json.loads(
        (results / "near_tie_diagnostic/near_tie_summary.json").read_text()
    )
    a3a, a3b = [], []
    for key, label in [
        ("17_industries", "17 industries"),
        ("14_countries", "14 countries"),
    ]:
        record = near[key]
        a3a.append(
            [
                label,
                record["endpoint_pairs"],
                record["literal_switches"],
                f'{record["median_initial_margin_bp"]["literal_switches"]:.2f}',
                f'{record["median_initial_margin_bp"]["literal_nonswitches"]:.2f}',
                format_percentage(
                    record[
                        "strict_pairwise_probability_switch_margin_lt_nonswitch_margin"
                    ]
                ),
            ]
        )
        split = record["margin_split_25bp"]
        cells = [
            format_percentage(split[k]["switch_rate"])
            + f' ({split[k]["literal_switches"]}/{split[k]["n"]})'
            for k in ("margin_le_25bp", "margin_gt_25bp")
        ]
        a3b.append([label, *cells])
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
                    (
                        format_basis_points(selected.endpoint_loss.mean())
                        if n >= 5
                        else "---"
                    ),
                    (
                        f"{int((selected.endpoint_loss > .0025).sum())}/{n}"
                        if n
                        else "---"
                    ),
                ]
            )
        a4.append(format_table_rows(method_rows))
    a5a = []
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
        a5a.append(
            [
                label,
                scheme,
                len(draws),
                format_interval_cell(
                    point["mean_endpoint_loss"], draws[key].quantile([0.025, 0.975])
                ),
            ]
        )
    a5b = []
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
        a5b.append(
            [
                h,
                format_interval_cell(
                    point, saved_interval("primary_17_definitive_B2000", key)
                ),
            ]
        )
    a5c = []
    for label, key, scale, signed in [
        ("Mean endpoint loss (bp)", "mean_endpoint_loss", 10000, False),
        ("Literal winner change", "literal_switch_frequency", 100, False),
        (r"Kaplan--Meier literal $S(12)$", "survival_12_months", 100, False),
        (r"Kaplan--Meier literal $S(24)$", "survival_24_months", 100, False),
        ("Correct selection rate", "selector_hit_rate", 100, False),
        ("Selection regret (bp)", "mean_selection_regret", 10000, False),
        (
            r"Selector $-$ ensemble CEQ (bp)",
            "mean_selector_minus_ensemble",
            10000,
            True,
        ),
    ]:
        a5c.append(
            [
                label,
                format_interval_cell(
                    country_summary[key], country_intervals[key], scale, signed
                ),
            ]
        )
    a6a = format_table_rows(
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
    a6b = []
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
        panel = pd.read_csv(
            root / "data/processed" / filename, index_col="date", parse_dates=True
        )
        a6b.append(
            [
                label + f" ($N={panel.shape[1]}$)",
                panel.index[0].strftime("%Y-%m")
                + "--"
                + panel.index[-1].strftime("%Y-%m"),
                panel.index[60].strftime("%Y-%m"),
                len(pairs),
                len(selections),
            ]
        )
    return {
        "table_1": [t1],
        "table_2": [t2],
        "table_A1": [a1, a1b],
        "table_A2": [a2a, a2b],
        "table_A3": [format_table_rows(a3a), format_table_rows(a3b)],
        "table_A4": a4,
        "table_A5": [
            format_table_rows(a5a),
            format_table_rows(a5b),
            format_table_rows(a5c),
        ],
        "table_A6": [a6a, format_table_rows(a6b)],
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


def assemble(root: Path, template_zip: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    working = output / "_export_work"
    build_working_bundle(root, working)
    tables, provenance = final_tables(root)
    (output / "tables").mkdir(exist_ok=True)
    (output / "figures").mkdir(exist_ok=True)
    (output / "sources").mkdir(exist_ok=True)
    with zipfile.ZipFile(template_zip) as archive:
        for name, bodies in tables.items():
            template = archive.read(f"tables/{name}.tex").decode("utf-8-sig")
            final = replace_table_bodies(template, bodies)
            if name == "table_A6":
                final = final.replace(
                    "Exact CEQ ties",
                    "Sample GMV uses divisor $L-1$; the centered empirical covariance inside the Ledoit--Wolf estimator uses divisor $L$. Exact CEQ ties",
                )
            if name == "table_A1":
                counts = provenance["specification_pair_counts"]
                note = (
                    f" Panel A uses specification-specific eligible samples: baseline {counts['baseline']} pairs, "
                    f"$L=36$ {counts['primary_17_L36']}, $L=120$ {counts['primary_17_L120']}, "
                    f"quarterly {counts['primary_17_quarterly']}; medians are full-sample Kaplan--Meier estimates, not common-origin medians."
                )
                final = final.replace(r"\end{table}", note + "\n" + r"\end{table}")
            (output / "tables" / f"{name}.tex").write_text(final, encoding="utf-8")
        for name in ("main.tex", "online_appendix.tex", "references.bib"):
            source = archive.read(name).decode("utf-8-sig")
            if name == "main.tex":
                source = source.replace(
                    "Online Appendix Sections F.1--F.2",
                    "Online Appendix Section F and Table A6",
                )
                source = source.replace(
                    r"12.1\%",
                    f"{provenance['primary_h24_common_material_pct']:.1f}" + r"\%",
                )
                source = source.replace(
                    r"(1-\lambda_t)S_t+\lambda_t\mu_t I",
                    r"(1-\lambda_t)C_t+\lambda_t\mu_t I",
                )
                source = source.replace(
                    r"\operatorname{tr}(S_t)/", r"\operatorname{tr}(C_t)/"
                )
                source = source.replace(
                    r"\operatorname{tr}(S_t)}", r"\operatorname{tr}(C_t)}"
                )
                source = source.replace(
                    "where $\\lambda_t$ denotes",
                    "where $C_t$ is the centered empirical covariance with divisor $L$ (in contrast to the divisor-$L-1$ covariance $S_t$ used for Sample GMV), and $\\lambda_t$ denotes",
                )
            (output / name).write_text(source, encoding="utf-8")
    for name in (
        "figure_1_winner_durability",
        "figure_2_endpoint_displacement",
        "figure_A1_transition_matrices",
        "figure_A2_leave_one_out",
    ):
        for suffix in (".pdf", ".png"):
            shutil.copy2(
                working / (name + suffix), output / "figures" / (name + suffix)
            )
    # Retire only this exporter's known intermediate filenames on a rerun.
    for path in working.glob("*.csv"):
        (output / "sources" / path.name).unlink(missing_ok=True)
    for path in working.glob("*.csv"):
        # Working CSVs remain explicit intermediate sources, not appendix floats.
        final_name = path.name
        for old, new in (
            ("table_A5", "table_A6"),
            ("table_A4", "table_A5"),
            ("table_A3", "table_A4"),
            ("source_A3", "source_A4"),
        ):
            if final_name.startswith(old):
                final_name = new + final_name[len(old) :]
                break
        shutil.copy2(path, output / "sources" / final_name)
    (output / "sources/publication_table_bodies.json").write_text(
        json.dumps(tables, indent=2), encoding="utf-8"
    )
    provenance["template_sha256"] = sha256(template_zip)
    provenance["table_data_sources"] = [
        "results/near_tie_diagnostic/near_tie_summary.json",
        "results/extension/primary17_gamma_cost_sensitivity.csv",
        "results/extension/materiality_threshold_sensitivity.csv",
        "results/extension/primary17_displacement.csv",
        "results/extension/countries_displacement.csv",
    ]
    provenance["scope"] = (
        "Export only; original frozen run directories and submitted ZIP preserved"
    )
    provenance["table_source_mapping"] = {
        "table_1": "Primary/country endpoint_pairs.csv and existing stationary outer_bootstrap.csv",
        "table_2": "Primary/country ex_ante_selection.csv and existing stationary outer_bootstrap.csv",
        "table_A1": "Baseline/L36/L120/quarterly summaries; extension gamma_cost and materiality_threshold CSVs",
        "table_A2": "Extension primary17/countries displacement CSVs; 17/30-industry summaries and draws",
        "table_A3": "results/near_tie_diagnostic/near_tie_summary.json",
        "table_A4": "Primary/country endpoint_pairs.csv grouped by earlier_winner",
        "table_A5": "Existing stationary/fixed-block draws; summaries; full-eligible displacement CSVs",
        "table_A6": "Validated processed panels and baseline endpoint/ex-ante counts; frozen method definitions",
    }
    (output / "EXPORT_MANIFEST.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# Repaired final publication source\n\nCompile main.tex and online_appendix.tex with pdfLaTeX. "
        "There are two main tables and exactly six appendix tables under tables/. "
        "All table data bodies are rebuilt from frozen outputs; layout/prose come from the submitted source ZIP. "
        "sources/ contains intermediate CSVs, not additional publication tables. "
        "_export_work/ is staging and is excluded from the release.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-zip",
        type=Path,
        default=project_root() / "replication/frozen_source.zip",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root() / "results/publication_final_repaired",
    )
    args = parser.parse_args()
    if not args.source_zip.exists():
        parser.error(
            "Frozen source template ZIP is missing; restore the replication bundle or specify --source-zip"
        )
    assemble(project_root(), args.source_zip, args.output_dir)
    print(f"Final publication source: {args.output_dir}")


if __name__ == "__main__":
    main()
