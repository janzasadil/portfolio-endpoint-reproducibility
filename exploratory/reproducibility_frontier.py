"""Describe endpoint reproducibility using saved pair losses only; never rebuild paths."""

from pathlib import Path

import numpy as np
import pandas as pd

SHIFTS = (6, 12, 24)
THRESHOLDS = (0, 10, 25, 50, 100)
SAMPLES = {
    "17_industries": ("17 U.S. industries", "primary17", "primary_17_definitive_B2000"),
    "14_countries": ("14 developed-country markets", "countries", "country_replication_B1000"),
}


def threshold_counts(losses, thresholds=THRESHOLDS):
    """Inclusive tolerances in CEQ bp; reject missing or negative saved losses."""
    values = np.asarray(losses, dtype=float)
    thresholds = np.asarray(thresholds, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Saved endpoint losses must be nonempty, finite, and nonnegative")
    if thresholds.ndim != 1 or not np.isfinite(thresholds).all() or (thresholds < 0).any():
        raise ValueError("Thresholds must be finite, nonnegative CEQ bp")
    return (values[:, None] <= thresholds[None, :] / 10000).sum(axis=0)


def build_frontier(root):
    source = root / "results/gap_perturbation_diagnostic/winner_change_audit_all_pairs.csv"
    audit = pd.read_csv(source, float_precision="round_trip")
    rows, validation = [], []
    for universe, (label, prefix, baseline) in SAMPLES.items():
        profile = pd.read_csv(root / f"results/extension/{prefix}_displacement.csv", float_precision="round_trip")
        canonical = pd.read_csv(root / f"results/{baseline}/endpoint_pairs.csv", float_precision="round_trip")
        for shift in SHIFTS:
            pairs = audit.loc[
                (audit.universe == universe)
                & (audit["sample"] == "december_full_eligible")
                & (audit.horizon_months == 120)
                & (audit.displacement_months == shift)
            ].copy()
            if pairs.empty or pairs.terminal_date.duplicated().any():
                raise ValueError(f"Missing or duplicate frozen endpoint losses: {universe}, h={shift}")
            dates = pd.to_datetime(pairs.terminal_date)
            later = pd.to_datetime(pairs.displaced_terminal_date)
            if not (dates.dt.month == 12).all() or not (
                later.dt.to_period("M").astype(int) - dates.dt.to_period("M").astype(int) == shift
            ).all():
                raise ValueError("Frozen dates do not match the requested December displacement")
            losses = pairs.endpoint_loss
            counts = threshold_counts(losses)
            expected = profile.loc[(profile.h == shift) & (profile["sample"] == "full_eligible")].iloc[0]
            metrics = {
                "mean_endpoint_loss": losses.mean(),
                "median_endpoint_loss": losses.median(),
                "p75_endpoint_loss": losses.quantile(.75),
                "p90_endpoint_loss": losses.quantile(.9),
                "literal_switch_frequency": pairs.reported_winner_change.mean(),
                "loss_exceeds_25bp_frequency": (losses > .0025).mean(),
                "n_origins": len(pairs),
            }
            for key, actual in metrics.items():
                if actual != expected[key]:
                    raise ValueError(f"Frozen headline mismatch: {universe}, h={shift}, {key}")
            for when in ("initial", "shifted"):
                columns = [f"{when}_ceq_{m}" for m in (
                    "equal_weight", "sample_gmv", "ledoit_wolf_gmv", "inverse_volatility", "erc"
                )]
                values = pairs[columns].to_numpy()
                if not np.isfinite(values).all():
                    raise ValueError("Missing frozen candidate CEQs")
                tie_count = int(((values == values.max(axis=1, keepdims=True)).sum(axis=1) > 1).sum())
                if when == "initial":
                    initial_ties = tie_count
                else:
                    later_ties = tie_count
            if not initial_ties and not later_ties and not np.array_equal(
                (losses > 0).to_numpy(), pairs.reported_winner_change.to_numpy()
            ):
                raise ValueError("Positive loss does not reproduce unique-winner switching")
            if shift == 12:
                saved = canonical.sort_values("earlier_endpoint").reset_index(drop=True)
                actual = pairs.sort_values("terminal_date").reset_index(drop=True)
                if not np.array_equal(actual.terminal_date, saved.earlier_endpoint) or not np.array_equal(
                    actual.endpoint_loss, saved.endpoint_loss
                ):
                    raise ValueError("h=12 losses do not match the canonical frozen baseline exactly")
            validation.append(f"{label}, h={shift}: n={len(pairs)}; exact top ties initial/later={initial_ties}/{later_ties}; all seven saved headline metrics match exactly.")
            for threshold, count in zip(THRESHOLDS, counts):
                rows.append(dict(universe=label, h_months=shift, threshold_bp=threshold,
                                 n_eligible=len(pairs), n_within_threshold=int(count),
                                 reproducibility_fraction=float(count / len(pairs))))
    return pd.DataFrame(rows), validation


def main(root=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    frontier, validation = build_frontier(root)  # Complete validation before writing anything.
    output = root / "results/reproducibility_frontier"
    output.mkdir(parents=True, exist_ok=True)
    frontier.to_csv(output / "frontier.csv", index=False)
    text = ["# Descriptive endpoint reproducibility frontier", "",
            "R(h, tau) = fraction of frozen eligible December comparisons with endpoint loss <= tau / 10,000. H=120 months. Tolerances are annualized CEQ bp. This is loss at the displaced endpoint, not first failure within h months, KM survival, inference, or a hypothesis test.", ""]
    for universe, (label, _, _) in SAMPLES.items():
        part = frontier.loc[frontier.universe == label]
        grid = part.pivot(index="h_months", columns="threshold_bp", values="reproducibility_fraction").loc[list(SHIFTS), list(THRESHOLDS)]
        text += [f"## {label}", "", "| h (months) | 0 bp | 10 bp | 25 bp | 50 bp | 100 bp |", "| ---: | ---: | ---: | ---: | ---: | ---: |"]
        for shift, row in grid.iterrows():
            text.append("| " + str(shift) + " | " + " | ".join(f"{100*v:.2f}%" for v in row) + " |")
        text += ["", "Eligible pairs at h=6/12/24: " + "/".join(str(int(part.loc[part.h_months == h, 'n_eligible'].iloc[0])) for h in SHIFTS) + ".", ""]
        fig, ax = plt.subplots(figsize=(6.5, 3.0), constrained_layout=True)
        image = ax.imshow(grid.to_numpy()*100, vmin=0, vmax=100, cmap="viridis", aspect="auto", interpolation="nearest")
        ax.set(xticks=range(5), xticklabels=THRESHOLDS, yticks=range(3), yticklabels=SHIFTS,
               xlabel="Tolerated endpoint loss (annualized CEQ bp)", ylabel="Endpoint displacement (months)", title=label)
        for i in range(3):
            for j in range(5):
                ax.text(j, i, f"{100*grid.iloc[i,j]:.1f}%", ha="center", va="center", color="black", fontsize=10)
        fig.colorbar(image, ax=ax, label="Reproducibility (%)", ticks=[0,25,50,75,100])
        fig.savefig(output / f"frontier_{universe}.png", dpi=200)
        plt.close(fig)
    text += ["## Interpretation", "",
        "At zero tolerance, reproducibility falls from 87.06% to 78.57% to 71.08% for industries and from 91.67% to 83.33% to 77.14% for countries as displacement increases from 6 to 12 to 24 months. The 6-to-24-month declines are 15.97 and 14.52 percentage points, respectively; these are discrete design comparisons, not estimated continuous slopes.", "",
        "Allowing 25 bp instead of zero raises industry reproducibility by 8.24, 15.48, and 16.87 percentage points at h=6/12/24. The corresponding country gains are 2.78, 5.56, and 5.71 points. Countries have greater literal winner stability at every displacement, yet slightly lower reproducibility at 25 bp: 94.44/88.89/82.86% versus 95.29/94.05/87.95%. Thus the difference is not simply one sample being more reproducible: industries switch more often, but a larger share of those switches is economically inexpensive. At h=12, 5/18 industry switches exceed 25 bp, versus 4/6 country switches; the country counts are small.", "",
        "Both surfaces are nondecreasing in tolerance, necessarily so for a fixed set of losses. Across displacement, industry reproducibility is nonincreasing at every threshold; country reproducibility is nonincreasing except at 100 bp, where it rises from 91.67% at 12 months to 94.29% at 24 months (33/36 to 33/35). Different eligible cohorts and possible recovery of the initial method mean endpoint-only reproducibility need not decline monotonically with displacement. This small reversal is descriptive, not evidence of a systematic improvement or statistical significance.", "",
        "## Added value: Moderately informative", "",
        "The frontier gives a useful synthesis of the distinction between winner identity and economically acceptable reproducibility. Its main cross-universe reversal is already largely visible in the existing switching and >25-bp summaries. The 10/50/100-bp columns clarify the distribution's steps and occasional nonmonotonicity, but do not establish a new inferential result. It is a potentially useful explanatory supplement, not an automatic recommendation for manuscript inclusion.", "",
        "## Validation and provenance", "",
        "All losses were read directly from results/gap_perturbation_diagnostic/winner_change_audit_all_pairs.csv, restricting to the two primary universes, H=120, december_full_eligible, and h=6/12/24. No monthly CEQs, portfolio paths, endpoint analyses, or bootstraps were reconstructed. The existing durability_surface CSVs were intentionally not used because they encode intervening first failure rather than the requested terminal-date loss.", "",
        "Canonical h=12 endpoint-loss arrays and dates match exactly. At h=12, R(12,0) is 1 minus the reported switching frequency, and R(12,25) is 1 minus the strict >25-bp loss frequency. At all three shifts, eligible count, mean/median/p75/p90 losses, switching, and >25-bp rates match the full-eligible rows of results/extension/{primary17,countries}_displacement.csv exactly. Inclusive <= comparisons in native units are the exact complement of strict > exceedance; no boundary rounding is applied.", ""]
    text += ["- " + line for line in validation]
    text += ["", "Both heatmaps use the same frontier.csv values, a shared 0–100% color scale, and discrete cells (no interpolation). All numerical rounding is for display only. Frozen outputs and manuscript/publication files remain unchanged.", ""]
    (output / "REPORT.md").write_text("\n".join(text), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
