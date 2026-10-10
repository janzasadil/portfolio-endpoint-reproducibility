"""Export two compact QF-style supplemental tables from validated saved diagnostics."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .ingest import project_root

SAMPLES = (("17_industries", "17 industries"), ("14_countries", "14 countries"))


def count_cell(count, fraction):
    return f"{int(count)} ({100*fraction:.1f}\\%)"


def tabular(columns, headings, rows):
    return (
        f"\\begin{{tabularx}}{{\\linewidth}}{{{columns}}}\n\\toprule\n"
        + " & ".join(h.replace(r"\makecell{", r"\makecell[t]{") for h in headings)
        + " \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabularx}\n"
    )


def table_frame(caption, label, body, note):
    return (
        "\\begin{table}[!htbp]\n\\centering\n\\small\n"
        + f"\\tbl{{{caption}}}{{\\begin{{minipage}}{{\\textwidth}}\\centering\n"
        + "\\footnotesize\n\\setlength{\\tabcolsep}{2pt}\n\\renewcommand{\\arraystretch}{1.22}\n"
        + body
        + "\\end{minipage}}\n"
        + "\\begin{tabnote}\\raggedright\\rightskip=\\tabledim plus 1fil\n"
        + "\\emph{Notes:} "
        + note
        + "\\par\n\\end{tabnote}\n"
        + f"\\label{{{label}}}\n\\end{{table}}\n"
    )


def table(caption, label, columns, headings, rows, note):
    return table_frame(caption, label, tabular(columns, headings, rows), note)


def build(root=None, output=None, *, input_root=None):
    root = Path(root) if root is not None else project_root()
    data_root = Path(input_root) if input_root is not None else root / "results"
    output = Path(output) if output is not None else root / "results/reproduced_publication"
    tables = output / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(
        data_root / "change_and_return/summary.csv", float_precision="round_trip"
    )
    origins = pd.read_csv(
        data_root / "change_and_return/origins.csv", float_precision="round_trip"
    )
    components = pd.read_csv(
        data_root / "return_risk_decomposition/summary.csv", float_precision="round_trip"
    )
    observations = pd.read_csv(
        data_root / "return_risk_decomposition/observations.csv", float_precision="round_trip"
    )
    displayed6 = []
    for universe, label in SAMPLES:
        for horizon in (12, 24):
            r = summary.loc[(summary.universe == universe) & (summary.h_months == horizon)].iloc[0]
            cohort = origins.loc[(origins.universe == universe) & (origins.h_months == horizon)]
            if len(cohort) != r.n_eligible:
                raise ValueError("A6 eligible counts differ from origin-level records")
            cells = [label, str(horizon)]
            for category in ("A", "B", "C", "A25", "B25", "C25"):
                field = "material_category" if category.endswith("25") else "literal_category"
                count = int((cohort[field] == category).sum())
                if count != r[f"{category}_count"] or not np.isclose(
                    count / len(cohort), r[f"{category}_share"], rtol=0, atol=1e-14
                ):
                    raise ValueError("A6 category does not reproduce saved origins")
                cells.append(count_cell(count, count / len(cohort)))
            displayed6.append(
                dict(
                    sample=label,
                    h_months=horizon,
                    n_eligible=len(cohort),
                    **{
                        category: cells[i + 2]
                        for i, category in enumerate(("A", "B", "C", "A25", "B25", "C25"))
                    },
                )
            )
    note6 = r"Entries are counts with percentages of eligible origins in parentheses. ``Returned by $h$'' denotes at least one earlier winner change with the initial winner first again at $h$; ``Within 25 bp again at $h$'' is defined analogously for the endpoint-loss threshold."

    def panel_rows(categories):
        result = []
        previous_sample = None
        for r in displayed6:
            if previous_sample is not None and r["sample"] != previous_sample:
                result.append(r"\addlinespace[0.55em]")
            previous_sample = r["sample"]
            cells = [r["sample"], str(r["h_months"]), str(r["n_eligible"])]
            cells += [r[c] for c in categories]
            result.append(" & ".join(cells) + r" \\")
        return result

    columns6 = r"@{}l c r *{3}{>{\centering\arraybackslash}X}@{}"
    common_headings = [
        r"\textbf{Sample}",
        r"\makecell{\textbf{Horizon}\\$h$ \textbf{(months)}}",
        r"$\boldsymbol{N}$",
    ]
    body6 = (
        r"\textbf{Panel A. Winner identity}\\[0.35em]"
        + "\n"
        + tabular(
            columns6,
            common_headings
            + [
                r"\makecell{\textbf{No change}\\\textbf{through} $h$}",
                r"\makecell{\textbf{Returned}\\\textbf{by} $h$}",
                r"\makecell{\textbf{Displaced}\\\textbf{at} $h$}",
            ],
            panel_rows(("A", "B", "C")),
        )
        + "\n"
        + r"\vspace{0.9em}"
        + "\n"
        + r"\textbf{Panel B. 25-bp endpoint-loss threshold}\\[0.35em]"
        + "\n"
        + tabular(
            columns6,
            common_headings
            + [
                r"\makecell{\textbf{Never} $>25$ \textbf{bp}\\\textbf{through} $h$}",
                r"\makecell{\textbf{Within 25 bp}\\\textbf{again at} $h$}",
                r"\makecell{$>25$ \textbf{bp}\\\textbf{at} $h$}",
            ],
            panel_rows(("A25", "B25", "C25")),
        )
    )
    a6 = table_frame(
        "First-passage events and fixed-horizon status",
        "tab:change-and-return",
        body6,
        note6,
    )
    rows, displayed7 = [], []
    for universe, label in SAMPLES:
        if rows:
            rows.append(r"\addlinespace[0.55em]")
        for subset, description in (
            ("all_winner_changes", "All winner changes"),
            ("loss_gt25bp", r"Loss $>25$ bp"),
        ):
            r = components.loc[
                (components.universe == universe) & (components.subset == subset)
            ].iloc[0]
            obs = observations.loc[
                (observations.universe == universe)
                & (True if subset == "all_winner_changes" else observations.loss_gt25bp)
            ]
            n = len(obs)
            median_mean = float(obs.delta_mean_component_bp.median())
            median_risk = float(obs.delta_risk_component_bp.median())
            dominant = int(
                (obs.delta_mean_component_bp.abs() > obs.delta_risk_component_bp.abs()).sum()
            )
            joint = int(
                ((obs.delta_mean_component_bp > 0) & (obs.delta_risk_component_bp > 0)).sum()
            )
            if (
                n != r.n
                or dominant != r.absolute_mean_dominates_count
                or joint != r.both_positive_count
                or not np.allclose(
                    [median_mean, median_risk],
                    [r.delta_mean_median_bp, r.delta_risk_median_bp],
                    rtol=0,
                    atol=1e-10,
                )
            ):
                raise ValueError("A7 summaries do not reproduce individual observations")
            cells = [
                label,
                description,
                str(n),
                f"{median_mean:.2f}",
                f"{median_risk:.2f}",
                count_cell(dominant, dominant / n),
                count_cell(joint, joint / n),
            ]
            rows.append(" & ".join(cells) + r" \\")
            displayed7.append(
                dict(
                    sample=label,
                    subset=subset,
                    n=n,
                    median_return_component_bp=median_mean,
                    median_risk_component_bp=median_risk,
                    return_dominates_count=dominant,
                    both_favor_count=joint,
                )
            )
    note7 = r"For shifted-window winner $m$ and initial winner $i$, $\delta^\mu=12\Delta(\bar r_m-\bar r_i)$ and $\delta^\sigma=-6\gamma\Delta(s_m^2-s_i^2)$, where $\Delta$ denotes shifted minus initial window and $\gamma=5$. Both components are reported in annualized CEQ bp. For both components, positive values favor the shifted-window winner."
    a7 = table(
        r"Return and risk components of 12-month winner changes",
        "tab:return-risk-components",
        r"@{}l l r *{4}{>{\centering\arraybackslash}X}@{}",
        [
            r"\textbf{Sample}",
            r"\textbf{Subset}",
            r"$\boldsymbol{n}$",
            r"\makecell{\textbf{Median}\\$\delta^\mu$}",
            r"\makecell{\textbf{Median}\\$\delta^\sigma$}",
            r"$|\delta^\mu|>|\delta^\sigma|$",
            r"\makecell{\textbf{Both favor}\\\textbf{shifted winner}}",
        ],
        rows,
        note7,
    )
    inputs = {
        "table_A6": ["change_and_return/summary.csv", "change_and_return/origins.csv"],
        "table_A7": ["return_risk_decomposition/summary.csv", "return_risk_decomposition/observations.csv"],
    }
    for name, contents in (("table_A6", a6), ("table_A7", a7)):
        header = (
            "% AUTO-GENERATED FILE. DO NOT EDIT BY HAND.\n"
            "% Generated by portfolio_endpoint.supplement_tables\n"
            + "".join("% Source: sources/" + source + "\n" for source in inputs[name])
        )
        (tables / (name + ".tex")).write_text(header + contents, encoding="utf-8", newline="\n")
    manifest = {
        "generator": "portfolio_endpoint.supplement_tables",
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {
            source: hashlib.sha256((data_root / source).read_bytes()).hexdigest()
            for sources in inputs.values() for source in sources
        },
        "tables": {
            name: hashlib.sha256((tables / (name + ".tex")).read_bytes()).hexdigest()
            for name in inputs
        },
    }
    (output / "SUPPLEMENT_A6_A7_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sources = output / "sources/supplement_A6_A7"
    sources.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(displayed6).to_csv(sources / "table_A6_display.csv", index=False)
    pd.DataFrame(displayed7).to_csv(sources / "table_A7_display.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build(project_root(args.root), args.output_dir)

if __name__ == "__main__":
    main()
