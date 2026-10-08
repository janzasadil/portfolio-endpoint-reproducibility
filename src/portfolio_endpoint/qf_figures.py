"""Regenerate the four QF V4 figures from frozen saved diagnostics.

No portfolio construction, CEQ estimation, endpoint analysis or resampling.
CSV ledgers preserve every plotted numerical value before display rounding.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER, kaplan_meier

METHOD_LABELS = dict(
    zip(
        TIE_BREAK_ORDER,
        ("Equal weight", "Sample GMV", "Ledoit--Wolf GMV", "Inverse volatility", "ERC"),
    )
)
ASSET_LABELS = {
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
FIGURE_NAMES = (
    "figure_1_winner_durability",
    "figure_2_endpoint_displacement",
    "figure_A1_transition_matrices",
    "figure_A2_leave_one_out",
)


def figure_inputs(root: Path) -> dict[str, pd.DataFrame]:
    """Construct only plotting ledgers from already frozen outputs."""
    survival, displacement, transitions, influence = [], [], [], []
    for sample, title, run, prefix, literal, material in (
        (
            "17_industries",
            "17 industries",
            "primary_17_definitive_B2000",
            "primary17",
            "diagnostics/survival_origin_audit_17_baseline.csv",
            "diagnostics/material_origin_audit_17_baseline.csv",
        ),
        (
            "14_countries",
            "14 countries",
            "country_replication_B1000",
            "countries",
            "extension/countries_literal_origin_audit.csv",
            "extension/countries_material25_origin_audit.csv",
        ),
    ):
        for definition, filename in [("Winner change", literal), ("Loss >25 bp", material)]:
            audit = pd.read_csv(root / "results" / filename)
            if audit.event.dtype != bool:
                raise ValueError("Survival event flags must be Boolean")
            curve = kaplan_meier(audit.rename(columns={"survival_duration_months": "time_months"}))
            survival.append(
                curve.assign(
                    sample=sample, title=title, definition=definition, n_origins=len(audit)
                )
            )
        profile = pd.read_csv(root / "results/extension" / f"{prefix}_displacement.csv")
        common = profile.loc[profile["sample"] == "common_calendar_origins"].sort_values("h")
        if common.h.tolist() != [6, 12, 24] or common.n_origins.nunique() != 1:
            raise ValueError("Displacement figure requires common origins at 6, 12, 24 months")
        displacement.append(common.assign(universe=sample, title=title))
        pairs = pd.read_csv(root / "results" / run / "endpoint_pairs.csv")
        counts = pd.crosstab(pairs.earlier_winner, pairs.later_winner).reindex(
            index=TIE_BREAK_ORDER, columns=TIE_BREAK_ORDER, fill_value=0
        )
        saved = pd.read_csv(
            root / "results/extension" / f"{prefix}_transition_counts.csv", index_col=0
        )
        np.testing.assert_array_equal(
            counts.to_numpy(), saved.loc[list(TIE_BREAK_ORDER), list(TIE_BREAK_ORDER)].to_numpy()
        )
        for initial in TIE_BREAK_ORDER:
            n = int(counts.loc[initial].sum())
            for shifted in TIE_BREAK_ORDER:
                count = int(counts.loc[initial, shifted])
                transitions.append(
                    {
                        "sample": sample,
                        "title": title,
                        "initial": initial,
                        "shifted": shifted,
                        "count": count,
                        "n_origins": n,
                        "percent": 100 * count / n if n else np.nan,
                    }
                )
        summary = json.loads((root / "results" / run / "summary.json").read_text())
        loo = pd.read_csv(root / "results/extension" / f"{prefix}_leave_one_out.csv")
        loo["influence_shift_bp"] = 10000 * (loo.mean_endpoint_loss - summary["mean_endpoint_loss"])
        loo["display_asset"] = loo.omitted_asset.replace(ASSET_LABELS)
        influence.append(loo.assign(sample=sample, title=title))
    return dict(
        zip(
            FIGURE_NAMES,
            (
                pd.concat(survival, ignore_index=True),
                pd.concat(displacement, ignore_index=True),
                pd.DataFrame(transitions),
                pd.concat(influence, ignore_index=True),
            ),
        )
    )


def render_figures(root: Path, destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError("Choose a fresh figure directory")
    ledgers = figure_inputs(root)
    destination.mkdir(parents=True)

    def save(fig, name):
        fig.savefig(destination / (name + ".pdf"), metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)
        ledgers[name].to_csv(destination / (name + "_source.csv"), index=False)

    with plt.rc_context({"font.size": 10, "pdf.fonttype": 42}):
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), sharey=True)
        fig.subplots_adjust(left=0.08, right=0.99, bottom=0.18, top=0.80, wspace=0.035)
        for ax, (title, group) in zip(axes, ledgers[FIGURE_NAMES[0]].groupby("title", sort=False)):
            for definition, curve in group.groupby("definition", sort=False):
                ax.step(
                    [0, *curve.time_months], [1, *curve.survival], where="post", label=definition
                )
            ax.set(
                title=title,
                xlabel="Months since initial terminal date",
                xlim=(0, 150),
                ylim=(0, 1.02),
            )
        axes[0].set_ylabel("Kaplan--Meier survival probability")
        fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, frameon=False)
        save(fig, FIGURE_NAMES[0])
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
        fig.subplots_adjust(left=0.09, right=0.99, bottom=0.19, top=0.78, wspace=0.035)
        for ax, (title, group) in zip(axes, ledgers[FIGURE_NAMES[1]].groupby("title", sort=False)):
            for column, label in [
                ("literal_switch_frequency", "Winner change"),
                ("loss_exceeds_25bp_frequency", "Loss >25 bp"),
            ]:
                ax.plot(group.h, 100 * group[column], marker="o", linewidth=2, label=label)
            ax.set(title=title, xlabel="Terminal-date displacement (months)", xticks=[6, 12, 24])
        axes[0].set_ylabel("Share of terminal dates (%)")
        fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, frameon=False)
        save(fig, FIGURE_NAMES[1])
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout="constrained")
        for ax, (title, group) in zip(axes, ledgers[FIGURE_NAMES[2]].groupby("title", sort=False)):
            matrix = group.pivot(index="initial", columns="shifted", values="percent").reindex(
                index=TIE_BREAK_ORDER, columns=TIE_BREAK_ORDER
            )
            n = group.groupby("initial").n_origins.first()
            image = ax.imshow(matrix.fillna(0), vmin=0, vmax=100, cmap="Blues")
            for i in range(5):
                for j in range(5):
                    value = matrix.iloc[i, j]
                    ax.text(
                        j,
                        i,
                        "--" if pd.isna(value) else f"{value:.0f}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if value >= 55 else "black",
                    )
            ax.set(
                title=title,
                xticks=range(5),
                yticks=range(5),
                xticklabels=list(METHOD_LABELS.values()),
                yticklabels=[f"{METHOD_LABELS[m]} (n={n[m]})" for m in TIE_BREAK_ORDER],
                xlabel="Winner after 12 months",
                ylabel="Initial winner",
            )
            plt.setp(ax.get_xticklabels(), rotation=38, ha="right")
        fig.colorbar(image, ax=axes, label="Row percentage", shrink=0.85)
        save(fig, FIGURE_NAMES[2])
        fig, axes = plt.subplots(1, 2, figsize=(10, 5), layout="constrained")
        for ax, (title, group) in zip(axes, ledgers[FIGURE_NAMES[3]].groupby("title", sort=False)):
            group = group.sort_values("influence_shift_bp", ascending=False)
            ax.plot(group.influence_shift_bp, range(len(group)), "o")
            ax.axvline(0, ls="--", color="black")
            ax.set(
                title=title,
                yticks=range(len(group)),
                yticklabels=group.display_asset,
                xlabel="Change in mean endpoint loss (bp)",
            )
            ax.invert_yaxis()
        save(fig, FIGURE_NAMES[3])
    evidence = {
        "scope": "Frozen saved-output plotting only; no new empirical analysis",
        "figures": list(FIGURE_NAMES),
        "plotted_rows": {name: len(frame) for name, frame in ledgers.items()},
        "displacement": "Common-origin winner-change and >25-bp shares, descriptive, no new CIs",
        "survival": "Full-sample Kaplan-Meier first-event curves",
        "leave_one_out": "Signed mean-loss change relative to full universe; no new CIs",
        "transition_counts": "Exactly match saved transition counts",
    }
    (destination / "FIGURE_REGENERATION.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    return evidence
