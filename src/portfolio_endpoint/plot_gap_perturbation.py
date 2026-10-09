"""Plot gap/perturbation geometry from validated saved winner changes."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER, _winner, ceq

from .supplement_inputs import SAMPLES, read_frozen
from .ceq_component_decomposition import reversal_points

GAP_CAPTION_TEX = (
    r"Gap--perturbation decomposition among winner changes, $H=120$ and $h=12$ months. "
    r"Each point represents one winner change, with the initial CEQ gap on the horizontal axis "
    r"and the shifted winner's relative CEQ change on the vertical axis. "
    r"The solid line $y=x$ is the zero-loss boundary and the dashed line $y=x+25$ "
    r"the 25-bp endpoint-loss boundary; vertical distance above $y=x$ equals endpoint loss. "
    r"The lines represent exact identities, not estimated relationships."
)


def write_gap_caption(output):
    """Ready-to-insert caption; figure image and saved points need not be regenerated."""
    (output / "caption.tex").write_text(
        "\\caption{" + GAP_CAPTION_TEX + "}\n" + "\\label{fig:gap-perturbation-winner-changes}\n",
        encoding="utf-8",
    )


def gap_figure(root, points, *, write_points=True):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = root / "results/gap_perturbation_scatter"
    output.mkdir(parents=True, exist_ok=True)
    if write_points:
        points.to_csv(output / "points.csv", index=False)
    plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42, "svg.fonttype": "none"})
    fig, axes = plt.subplots(
        1, 2, figsize=(8.8, 4.6), sharex=True, sharey=True, layout="constrained"
    )
    bound = max(points.initial_gap_bp.max(), points.relative_ceq_change_bp.max(), 25) * 1.10
    x = np.array([0, bound])
    for ax, (universe, (label, _, _)) in zip(axes, SAMPLES.items()):
        selected = points.loc[points.universe == universe]
        ax.plot(x, x, color="0.20", lw=1.5, label="Zero loss: y = x")
        ax.plot(
            x,
            x + 25,
            color="0.55",
            lw=1.7,
            ls=(0, (5, 3)),
            label="25-bp loss: y = x + 25",
        )
        for material, color, marker, label2 in (
            (False, "#3274A1", "o", r"Loss $\leq$25 bp"),
            (True, "#D55E00", "^", "Loss >25 bp"),
        ):
            group = selected.loc[selected.loss_gt25bp == material]
            ax.scatter(
                group.initial_gap_bp,
                group.relative_ceq_change_bp,
                s=38,
                c=color,
                marker=marker,
                edgecolors="white",
                linewidths=0.5,
                label=label2,
                zorder=3,
            )
        ax.set(
            xlim=(-0.02 * bound, bound),
            ylim=(-0.02 * bound, bound),
            xlabel="Initial CEQ gap (bp)",
            title=f"{label}\nn={len(selected)}; >25 bp: {int(selected.loss_gt25bp.sum())}",
        )
        ax.grid(alpha=0.15)
    axes[0].set_ylabel("Relative CEQ change (bp)")
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        frameon=False,
        fontsize=9,
        loc="outside lower center",
        ncol=2,
        columnspacing=2.5,
        handlelength=3,
    )
    pdf = root / "output/pdf/gap_perturbation_scatter.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(pdf)
    fig.savefig(output / "gap_perturbation_scatter.png", dpi=250)
    fig.savefig(output / "gap_perturbation_scatter.svg")
    plt.close(fig)
    write_gap_caption(output)
    lines = [
        "# Gap-perturbation scatter: observed winner changes",
        "",
        "## Publication caption",
        "",
        GAP_CAPTION_TEX,
        "",
        "The ready-to-insert LaTeX caption is in caption.tex. The plot is conditional on winner changes; non-change observations are not plotted.",
        "",
        "H=120, h=12; shifted-window winner m versus initial winner i. x = Q_i(e)-Q_m(e); y = [Q_m(e+h)-Q_m(e)]-[Q_i(e+h)-Q_i(e)]. All axes and CSV quantities are annualized CEQ bp. Vertical distance y-x is the endpoint loss. No regression, smoother, trend fit or inference is used.",
        "",
        "| Universe | Plotted winner changes | Above 25-bp line |",
        "| --- | ---: | ---: |",
    ]
    for universe in SAMPLES:
        group = points.loc[points.universe == universe]
        lines.append(f"| {universe} | {len(group)} | {int(group.loss_gt25bp.sum())} |")
    lines += [
        "",
        "All y-x losses match stored losses to 1e-12 native units; every changed-winner point is above y=x (no exact tied winner changes). Classification above y=x+25 matches strict stored loss >25 bp exactly. Both panels share identical axis limits. The shared legend sits below the panels; the zero-loss reference is dark solid and the 25-bp reference is lighter with long dashes. Point labels are omitted to avoid unexplained bookkeeping codes; points.csv retains IDs (US = industry sample, INT = country sample; numbers enumerate winner-change observations in chronological order).",
        "",
        "**Useful only in supplement; retain only as reviewer-response material for now.** The plot makes the threshold geometry tangible but the loss-gap identity is algebraic and the materiality counts are already reported. The country panel has only six winner changes, so its scatter is not evidence of a general relationship. It may help explain the equation to readers, but is not a separate empirical contribution or an inferential diagram; do not automatically add another figure.",
        "",
        "Figure: output/pdf/gap_perturbation_scatter.pdf; editable vector copy and preview in this directory. Manuscript and publication sources are unchanged.",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")



def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    root = parser.parse_args().root
    gap_figure(root, reversal_points(read_frozen(root)))

if __name__ == "__main__":
    main()
