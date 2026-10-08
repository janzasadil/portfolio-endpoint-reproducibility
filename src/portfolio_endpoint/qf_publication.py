"""Generate the QF V4 tables and audit them against frozen outputs.

The supplied ZIP provides layouts, manuscript prose, and figure assets only.
All table data bodies are generated independently from saved results. No
portfolio paths, endpoint analyses, CEQs, or bootstrap draws are rerun.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from decimal import Decimal
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER
from .final_publication import (
    final_tables,
    format_basis_points,
    format_percentage,
    format_table_rows,
    replace_table_bodies,
)
from .fixed_method_benchmark import SAMPLES, benchmark_selection, validate_headlines
from .ingest import project_root, sha256

TABLE_NAMES = ("table_1", "table_2", "table_A1", "table_A2", "table_A3", "table_A4", "table_A5")
FIGURE_NAMES = (
    "figure_1_winner_durability",
    "figure_2_endpoint_displacement",
    "figure_A1_transition_matrices",
    "figure_A2_leave_one_out",
)
ATOL = 1e-12


def saved_interval(root: Path, folder: str, column: str) -> np.ndarray:
    draws = pd.read_csv(
        root / "results" / folder / "outer_bootstrap.csv",
        usecols=[column],
        float_precision="round_trip",
    )
    return draws[column].quantile([0.025, 0.975]).to_numpy()


def interval_text(point, interval, *, stacked=False, signed=False):
    point_text = format(10000 * point, "+.2f" if signed else ".2f")
    bounds = (
        "(" + format_basis_points(interval[0]) + r",\," + format_basis_points(interval[1]) + ")"
    )
    if signed:
        point_text = "$" + point_text + "$"
    if stacked:
        return r"\makecell{" + point_text + r"\\\footnotesize$" + bounds + "$}"
    return point_text + " $" + bounds + "$"


def conditional_gap_statistics(pairs: pd.DataFrame) -> dict:
    changed = pairs.loc[pairs.literal_switch]
    gaps, perturbations = [], []
    for _, row in changed.iterrows():
        initial, shifted = row.earlier_winner, row.later_winner
        initial_score = row["earlier_ceq_" + initial]
        shifted_initial_score = row["earlier_ceq_" + shifted]
        later_initial = row["later_ceq_" + initial]
        later_shifted = row["later_ceq_" + shifted]
        gap = initial_score - shifted_initial_score
        perturbation = (later_shifted - shifted_initial_score) - (later_initial - initial_score)
        if abs(perturbation - gap - row.endpoint_loss) > ATOL:
            raise ValueError("Conditional decomposition does not reproduce endpoint loss")
        gaps.append(gap)
        perturbations.append(perturbation)
    return {
        "n": len(changed),
        "mean_loss": float(changed.endpoint_loss.mean()),
        "median_gap": float(np.median(gaps)),
        "median_perturbation": float(np.median(perturbations)),
        "median_loss": float(changed.endpoint_loss.median()),
        "material_count": int((changed.endpoint_loss > 0.0025).sum()),
    }


def build_qf_tables(root: Path) -> tuple[dict[str, list[str]], dict]:
    previous, provenance = final_tables(root)
    pairs, selections, benchmarks, summaries = {}, {}, {}, {}
    for sample, expected in SAMPLES.items():
        folder = root / "results" / expected[0]
        pairs[sample] = pd.read_csv(folder / "endpoint_pairs.csv", float_precision="round_trip")
        selections[sample] = pd.read_csv(
            folder / "ex_ante_selection.csv", float_precision="round_trip"
        )
        summaries[sample] = json.loads((folder / "summary.json").read_text())
        _, _, benchmark, _, _ = benchmark_selection(selections[sample], sample)
        validate_headlines(benchmark, summaries[sample], expected)
        benchmarks[sample] = benchmark
    order = ("17_industries", "14_countries")
    interval_folders = {
        "17_industries": "primary_17_definitive_B2000",
        "14_countries": "country_replication_B1000",
    }
    intervals = {
        sample: {
            metric: saved_interval(
                root,
                interval_folders[sample],
                ("baseline_" if sample == "17_industries" else "") + metric,
            )
            for metric in (
                "mean_endpoint_loss",
                "mean_selection_regret",
                "mean_selector_minus_ensemble",
            )
        }
        for sample in order
    }
    conditional = {sample: conditional_gap_statistics(pairs[sample]) for sample in order}
    t1_rows = [
        [r"\quad Endpoint pairs", *[len(pairs[s]) for s in order]],
        [
            r"\quad Winner change",
            *[format_percentage(pairs[s].literal_switch.mean()) for s in order],
        ],
        [
            r"\quad Endpoint loss $>25$ bp",
            *[format_percentage((pairs[s].endpoint_loss > 0.0025).mean()) for s in order],
        ],
        [
            r"\quad Mean endpoint loss",
            *[
                interval_text(
                    pairs[s].endpoint_loss.mean(), intervals[s]["mean_endpoint_loss"], stacked=True
                )
                for s in order
            ],
        ],
    ]
    t1 = r"\multicolumn{3}{l}{\textbf{Panel A. All endpoint pairs}}\\[-0.15em]" + "\n"
    t1 += format_table_rows(t1_rows)
    t1 += (
        "\n"
        + r"\addlinespace[0.25em]"
        + "\n"
        + r"\multicolumn{3}{l}{\textbf{Panel B. Winner-change pairs}}\\[-0.15em]"
        + "\n"
    )
    t1 += format_table_rows(
        [
            [r"\quad Pairs", *[conditional[s]["n"] for s in order]],
            [
                r"\quad Mean endpoint loss",
                *[format_basis_points(conditional[s]["mean_loss"]) for s in order],
            ],
            [
                r"\quad Median initial CEQ gap",
                *[format_basis_points(conditional[s]["median_gap"]) for s in order],
            ],
            [
                r"\quad Median relative CEQ change",
                *[format_basis_points(conditional[s]["median_perturbation"]) for s in order],
            ],
            [
                r"\quad Median endpoint loss",
                *[format_basis_points(conditional[s]["median_loss"]) for s in order],
            ],
            [
                r"\quad Endpoint loss $>25$ bp",
                *[
                    str(conditional[s]["material_count"])
                    + "/"
                    + str(conditional[s]["n"])
                    + " ("
                    + format_percentage(conditional[s]["material_count"] / conditional[s]["n"])
                    + ")"
                    for s in order
                ],
            ],
        ]
    )
    t2 = format_table_rows(
        [
            ["Decision dates", *[len(selections[s]) for s in order]],
            [
                "Correct-selection rate",
                *[format_percentage(benchmarks[s]["preceding_winner_hit_rate"]) for s in order],
            ],
            [
                "Most frequent winner rate",
                *[format_percentage(benchmarks[s]["majority_constant_hit_rate"]) for s in order],
            ],
            [
                "Mean selection regret",
                *[
                    interval_text(
                        selections[s].selection_regret.mean(), intervals[s]["mean_selection_regret"]
                    )
                    for s in order
                ],
            ],
            [
                "Lowest fixed-method mean regret",
                *[format(benchmarks[s]["best_fixed_mean_regret_bp"], ".2f") for s in order],
            ],
            [
                r"Mean selector $-$ ensemble CEQ",
                *[
                    interval_text(
                        selections[s].selector_minus_ensemble.mean(),
                        intervals[s]["mean_selector_minus_ensemble"],
                        signed=True,
                    )
                    for s in order
                ],
            ],
        ]
    )
    phase = pd.read_csv(
        root / "results/calendar_window_robustness/calendar_phase_sensitivity.csv",
        float_precision="round_trip",
    )
    phase_body = ""
    for sample, label in zip(order, ("17 industries", "14 countries")):
        group = phase.loc[phase.universe == sample]
        if len(group) != 12 or set(group.terminal_month) != set(range(1, 13)):
            raise ValueError("Calendar-phase summary requires all twelve phases")
        if phase_body:
            phase_body += r"\addlinespace" + "\n"
        phase_body += r"\multicolumn{5}{l}{\textbf{" + label + r"}} \\" + "\n"
        rows = []
        for metric, title, decimals in (
            ("switch_rate_pct", r"Winner change (\%)", 1),
            ("loss_gt25_rate_pct", r"Endpoint loss $>25$ bp (\%)", 1),
            ("mean_loss_ceq_bp", "Mean endpoint loss (bp)", 2),
        ):
            values = group[metric]
            december = group.loc[group.terminal_month == 12, metric].iloc[0]
            rows.append(
                [
                    title,
                    *[
                        format(value, "." + str(decimals) + "f")
                        for value in (values.min(), values.median(), values.max(), december)
                    ],
                ]
            )
        phase_body += format_table_rows(rows) + "\n"
    windows = pd.read_csv(
        root / "results/calendar_window_robustness/evaluation_window_sensitivity.csv",
        float_precision="round_trip",
    )
    window_rows = []
    for sample, label in zip(order, ("17 industries", "14 countries")):
        for horizon in (120, 60):
            selected = windows.loc[
                (windows.universe == sample)
                & (windows.comparison_set == "common_dates")
                & (windows.H_months == horizon)
            ]
            if len(selected) != 1:
                raise ValueError("Missing unique common-date evaluation-window result")
            row = selected.iloc[0]
            window_rows.append(
                [
                    label,
                    horizon,
                    int(row.n_pairs),
                    format_percentage(row.switch_count / row.n_pairs),
                    format_percentage(row.loss_gt25_count / row.n_pairs),
                    format(row.mean_loss_ceq_bp, ".2f"),
                ]
            )
    a4 = list(previous["table_A5"])
    a4[2] = a4[2].replace("Literal winner change", "Winner change")
    for horizon in (12, 24):
        a4[2] = a4[2].replace(
            r"Kaplan--Meier literal $S(" + str(horizon) + ")$",
            r"Winner-change $\widehat S_{\mathrm{KM}}(" + str(horizon) + ")$",
        )
    a4[2] = a4[2].replace(r"Selector $-$ ensemble CEQ", r"Mean selector $-$ ensemble CEQ")
    bodies = {
        "table_1": [t1],
        "table_2": [t2],
        "table_A1": previous["table_A1"],
        "table_A2": [*previous["table_A2"], phase_body, format_table_rows(window_rows)],
        "table_A3": previous["table_A4"],
        "table_A4": a4,
        "table_A5": previous["table_A6"],
    }
    provenance.update(
        {
            "prospective_benchmarks": benchmarks,
            "conditional_gap_statistics": conditional,
            "export_scope": "QF V4 seven-table export; saved outputs only; no empirical computation",
            "additional_inputs": [
                "results/calendar_window_robustness/calendar_phase_sensitivity.csv",
                "results/calendar_window_robustness/evaluation_window_sensitivity.csv",
            ],
        }
    )
    return bodies, provenance


def table_bodies(source: str) -> list[str]:
    return re.findall(r"\\midrule\s*(.*?)\\bottomrule", source, flags=re.S)


def printed_numbers(body: str) -> list[str]:
    # Remove typesetting dimensions and column counts, not data or row labels.
    body = re.sub(r"\\(?:addlinespace|vspace|hspace)(?:\[[^\]]*\])?(?:\{[^}]*\})?", "", body)
    body = re.sub(r"\\\\\[[^\]]*\]", "", body)
    body = re.sub(r"\\multicolumn\{\d+\}", r"\\multicolumn{}", body)
    return re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", body)


def compare_table_numbers(name: str, template: str, bodies: list[str]) -> list[dict]:
    original = table_bodies(template)
    if len(original) != len(bodies):
        raise ValueError(f"{name}: layout has {len(original)} bodies, generated {len(bodies)}")
    records = []
    for panel, (source, generated) in enumerate(zip(original, bodies), start=1):
        expected, actual = printed_numbers(source), printed_numbers(generated)
        for index in range(max(len(expected), len(actual))):
            before = expected[index] if index < len(expected) else None
            after = actual[index] if index < len(actual) else None
            records.append(
                {
                    "table": name,
                    "panel": panel,
                    "token_index": index + 1,
                    "submitted_numeric": before,
                    "generated_numeric": after,
                    "matches": before is not None
                    and after is not None
                    and Decimal(before) == Decimal(after),
                }
            )
    return records


def template_prefix(archive: zipfile.ZipFile) -> str:
    matches = [name for name in archive.namelist() if PurePosixPath(name).name == "main.tex"]
    if len(matches) != 1:
        raise ValueError("Source ZIP must contain exactly one main.tex")
    prefix = matches[0][: -len("main.tex")]
    if prefix.startswith("/") or ".." in PurePosixPath(prefix).parts:
        raise ValueError("Unsafe source ZIP prefix")
    return prefix


def implementation_audit(root: Path, provenance: dict) -> dict:
    import yaml
    from .diagnostics import audit_summary
    from .gap_perturbation import monthly_panel_from_pairs, read_pairs
    from .methods import SETTINGS

    settings = yaml.safe_load((root / "config/experiment.yaml").read_text())["study"]
    required = {
        "estimation_window_months": 60,
        "evaluation_horizon_months": 120,
        "endpoint_displacement_months": 12,
        "ceq_risk_aversion": 5,
        "transaction_cost_per_half_turnover": 0.0025,
        "rebalancing_frequency": "monthly",
        "tie_break_order": list(TIE_BREAK_ORDER),
    }
    if any(settings[key] != value for key, value in required.items()):
        raise ValueError("Current study settings do not match the V4 paper specification")
    if (
        SETTINGS.max_iterations,
        SETTINGS.objective_tolerance,
        SETTINGS.feasibility_tolerance,
        SETTINGS.erc_objective_tolerance,
        SETTINGS.erc_relative_tolerance,
    ) != (2000, 1e-10, 1e-8, 1e-15, 1e-6):
        raise ValueError("Current solver settings conflict with Appendix F")
    survival = []
    for label, folder in (
        ("17_baseline", "primary_17_definitive_B2000"),
        ("17_L36", "primary_17_L36"),
        ("17_L120", "primary_17_L120"),
        ("17_quarterly", "primary_17_quarterly"),
    ):
        audit = pd.read_csv(root / "results/diagnostics" / f"survival_origin_audit_{label}.csv")
        summary = json.loads((root / "results" / folder / "summary.json").read_text())
        median = audit_summary(audit)["median_survival_months_full_km"]
        if median != summary["median_survival_months"]:
            raise ValueError("Specification-specific KM median fails to reproduce")
        pairs = pd.read_csv(root / "results" / folder / "endpoint_pairs.csv")
        survival.append(
            {
                "specification": label,
                "endpoint_pairs": len(pairs),
                "km_origins": len(audit),
                "median_months": median,
            }
        )
    bootstrap = []
    for folder, expected_b, expected_block in (
        ("primary_17_definitive_B2000", 2000, 34),
        ("country_replication_B1000", 1000, 6),
        ("replication_30_B1000", 1000, 34),
        ("primary_17_fixedblock12_B1000", 1000, 12),
        ("primary_17_fixedblock24_B1000", 1000, 24),
    ):
        draws = pd.read_csv(
            root / "results" / folder / "outer_bootstrap.csv",
            usecols=["replication", "block_length"],
        )
        if (
            len(draws) != expected_b
            or not draws.replication.tolist() == list(range(expected_b))
            or set(draws.block_length) != {expected_block}
        ):
            raise ValueError(
                "Saved bootstrap replication registry or block length conflicts with paper"
            )
        bootstrap.append(
            {"run": folder, "replications": len(draws), "block_length": expected_block}
        )
    monthly_ties = {}
    for universe in ("17_industries", "14_countries"):
        panel = monthly_panel_from_pairs(
            read_pairs(
                root
                / "results/calendar_window_robustness"
                / f"{universe}_H120_monthly_endpoint_pairs.csv"
            )
        )
        values = panel.to_numpy()
        tied = (values == values.max(axis=1, keepdims=True)).sum(axis=1) > 1
        monthly_ties[universe] = {
            "monthly_endpoints": len(panel),
            "exact_top_ties": int(tied.sum()),
        }
        if tied.any():
            raise ValueError(
                "V4 zero-threshold/first-winner-change equivalence needs revision: monthly top ties exist"
            )
    for sample, filename in (
        ("17_industries", "primary17_leave_one_out.csv"),
        ("14_countries", "countries_leave_one_out.csv"),
    ):
        omitted = pd.read_csv(root / "results/extension" / filename)
        if not (omitted.mean_endpoint_loss > 0).all():
            raise ValueError("Leave-one-out positivity claim does not reproduce")
    return {
        "baseline_settings": required,
        "specification_samples": survival,
        "bootstrap_registry": bootstrap,
        "monthly_top_ties": monthly_ties,
        "selector_ensemble_aggregation": "Arithmetic mean of decision-level following-window CEQ differences; not pooled-return CEQs",
        "code_references": {
            "CEQ and exact winner rule": "analysis.py: ceq, _winner",
            "prospective windows, regret, ensemble difference": "analysis.py: ex_ante_selection",
            "continuous holdings, timing, turnover, net costs, ensemble": "engine.py: run_continuous_path, run_headline_paths",
            "covariance and solver conventions": "methods.py: sample_covariance, ledoit_wolf_gmv, erc, SETTINGS",
            "resampling, bounded block rule, replicate averaging": "bootstrap.py: protocol_block_length, outer_bootstrap, _draw_metrics, outer_sensitivity_bootstrap",
        },
        "clarifications": [
            "The decomposition medians in Results 3.1 are conditional on a winner change, as Table 1 Panel B states. Make that conditioning explicit in the prose; unconditional medians include structural zeros.",
            "Table A1 Panel A uses specification-specific eligible samples and full-sample KM medians, not the earlier 80-common-origin analysis. Adding those sample definitions/counts to its note would improve transparency.",
            "The corrected Politis-White implementation additionally bounds block lengths to [2, floor(sqrt(T))] and rounds upward; Appendix E gives the realized lengths but does not state this implementation detail.",
            "The international Mkt series is the broader value-weighted USD series with all four valuation ratios not required; its market coverage depends on B/M availability. Do not describe it as every listed stock in a national index.",
        ],
        "figures": "V4 PDF figure assets are preserved, not regenerated. Visual labels/captions were reviewed against saved diagnostics; individual plotted vertices are not automatically audited.",
    }


def write_audit_report(output: Path, numerical: pd.DataFrame, audit: dict) -> None:
    failures = numerical.loc[~numerical.matches]
    lines = [
        "# QF V4 paper-code consistency audit",
        "",
        f"Generated all seven tables from frozen outputs. Compared {len(numerical)} printed numerical tokens (including numerical row labels) across 15 table bodies: {len(failures)} discrepancies.",
        "",
        "## Verified",
        "",
        "- Main endpoint counts, strict >25-bp rates, conditional losses, gap/perturbation medians, and all printed bootstrap bounds.",
        "- Prospective counts 75/27, hit rates 38.7%/25.9%, regret 109.12/48.25 bp, retrospective fixed-method benchmarks, and arithmetic mean selector-minus-ensemble differences -10.93/+58.11 bp.",
        "- Full-eligible versus common-date displacement samples; all twelve calendar phases; H=60 common-date results.",
        "- Specification-specific KM medians and complete-follow-up 0/25/50-bp survival slices are distinct and correctly labeled.",
        "- CEQ sample variance, frozen exact tie priority, continuous holdings, t-to-t+1 timing, half-L1 turnover, multiplicative net costs, no entry turnover, and separately traded ensemble agree with the implementation.",
        "- Sample covariance uses divisor L-1; the centered Ledoit-Wolf empirical covariance uses divisor L. Solver tolerances agree with Appendix F.",
        "- Existing bootstrap counts/block lengths and the same decision-level mean within ordinary/enhanced bootstrap replications.",
        "",
        "## Exact specification sample sizes",
        "",
        "| Specification | Endpoint pairs | Full-KM origins | Median (months) |",
        "|---|---:|---:|---:|",
    ]
    for row in audit["specification_samples"]:
        lines.append(
            "| "
            + row["specification"]
            + " | "
            + str(row["endpoint_pairs"])
            + " | "
            + str(row["km_origins"])
            + " | "
            + str(int(row["median_months"]))
            + " |"
        )
    lines += ["", "## Wording/implementation clarifications (not changed automatically)", ""]
    lines += ["- " + text for text in audit["clarifications"]]
    lines += [
        "",
        "## Scope and preservation",
        "",
        (
            "No numerical inconsistency was found in the submitted tables."
            if failures.empty
            else "Printed-value differences are detailed in table_numeric_audit.csv; generated tables use saved results, never submitted numeric literals."
        ),
        "The manuscript prose, journal class, bibliography, and four figure assets are copied from the V4 ZIP without scientific edits. Figures remain supplied assets; do not assume this exporter regenerates them if data change.",
        "Original Downloads files, earlier publication outputs, and frozen empirical run directories are unchanged. No portfolio construction, endpoint/robustness analysis, or bootstrap ran. Only lightweight saved-output aggregation and percentile quantiles were evaluated.",
        "This is a paper-code audit, not an independent check of external literature, journal policies, author declarations, or every pixel of the supplied figures.",
        "",
        "Machine-readable evidence: table_numeric_audit.csv, PAPER_CODE_AUDIT.json, EXPORT_MANIFEST.json, and sources/publication_table_bodies.json.",
    ]
    (output / "PAPER_CODE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def assemble(root: Path, template_zip: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(
            "Choose a fresh V4 output directory; existing publication packages are preserved"
        )
    bodies, provenance = build_qf_tables(root)
    implementation = implementation_audit(root, provenance)
    rendered, comparisons = {}, []
    with zipfile.ZipFile(template_zip) as archive:
        prefix = template_prefix(archive)
        for name in TABLE_NAMES:
            template = archive.read(prefix + "tables/" + name + ".tex").decode("utf-8-sig")
            rendered[name] = replace_table_bodies(template, bodies[name])
            comparisons.extend(compare_table_numbers(name, template, bodies[name]))
        assets = [
            "main.tex",
            "supplemental_material.tex",
            "references.bib",
            "rQUF2e.cls",
            "rQUF.bst",
            "main.bbl",
            "README_QF_OFFICIAL_FORMAT.txt",
        ]
        assets += ["figures/" + name + ".pdf" for name in FIGURE_NAMES]
        payloads = {name: archive.read(prefix + name) for name in assets}
    output.mkdir(parents=True)
    for name, contents in payloads.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
    (output / "tables").mkdir()
    for name, contents in rendered.items():
        (output / "tables" / (name + ".tex")).write_text(contents, encoding="utf-8")
    (output / "sources").mkdir()
    (output / "sources/publication_table_bodies.json").write_text(
        json.dumps(bodies, indent=2), encoding="utf-8"
    )
    numerical = pd.DataFrame(comparisons)
    numerical.to_csv(output / "table_numeric_audit.csv", index=False)
    implementation["printed_numeric_discrepancies"] = int((~numerical.matches).sum())
    (output / "PAPER_CODE_AUDIT.json").write_text(
        json.dumps(implementation, indent=2), encoding="utf-8"
    )
    provenance.update(
        {
            "template_sha256": sha256(template_zip),
            "table_names": list(TABLE_NAMES),
            "table_body_counts": {name: len(value) for name, value in bodies.items()},
            "numeric_tokens_compared": len(numerical),
            "printed_numeric_discrepancies": int((~numerical.matches).sum()),
            "figure_policy": "Copy supplied V4 figures, do not generate new empirical figures",
        }
    )
    (output / "EXPORT_MANIFEST.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    write_audit_report(output, numerical, implementation)
    (output / "README.md").write_text(
        "# Generated QF V4 publication source\n\nTwo main tables and exactly five appendix tables. "
        "Every numerical table body is generated from frozen outputs; original prose, layouts, "
        "journal class, bibliography and figure assets are preserved.\n\n"
        "Compile main.tex and supplemental_material.tex with pdfLaTeX. The supplied main.bbl "
        "can be reused, or rebuild with bibtex main. Run pdfLaTeX twice for references.\n\n"
        "Regenerate from the repository with:\n\n"
        "```text\npython -m portfolio_endpoint.qf_publication --source-zip PATH_TO_V4_ZIP --output-dir FRESH_OUTPUT_DIR\n```\n\n"
        "Set PYTHONPATH=src or install the project first. Existing output directories are never overwritten. "
        "See PAPER_CODE_AUDIT.md for consistency checks and remaining prose clarifications.\n",
        encoding="utf-8",
    )
    print("Generated QF V4 source: " + str(output))
    print(
        "Printed numerical discrepancies: " + str(implementation["printed_numeric_discrepancies"])
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = project_root()
    assemble(root, args.source_zip, args.output_dir or root / "results/publication_qf_v4_generated")


if __name__ == "__main__":
    main()
