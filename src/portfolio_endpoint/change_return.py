"""A6 first-passage events and fixed-horizon status from frozen monthly CEQs."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER, _winner, ceq

from .supplement_inputs import SAMPLES, read_frozen

def change_return_categories(changed, losses, threshold=0.0025):
    """Classify one full monthly follow-up, with the origin winner held fixed."""
    changed = np.asarray(changed, dtype=bool)
    losses = np.asarray(losses, dtype=float)
    if changed.ndim != 1 or len(changed) == 0 or losses.shape != changed.shape:
        raise ValueError("Need synchronized nonempty monthly histories")
    if not np.isfinite(losses).all() or (losses < 0).any():
        raise ValueError("Loss histories must be finite and nonnegative")
    literal = "C" if changed[-1] else ("B" if changed.any() else "A")
    exceeded = losses > threshold
    material = "C25" if exceeded[-1] else ("B25" if exceeded.any() else "A25")
    return literal, material


def change_and_return(root, inputs):
    output = root / "results/change_and_return"
    records, summaries, validations = [], [], []
    for universe, (panel, full, _) in inputs.items():
        label, prefix, _ = SAMPLES[universe]
        literal = pd.read_csv(root / f"results/extension/{prefix}_literal_origin_audit.csv")
        material = pd.read_csv(root / f"results/extension/{prefix}_material25_origin_audit.csv")
        for shift in (12, 24):
            pairs = full.loc[full.displacement_months == shift]
            origin_sets = []
            for saved in (literal, material):
                origin_sets.append(
                    set(
                        pd.to_datetime(
                            saved.loc[saved.available_followup_months >= shift, "origin_date"]
                        ).dt.to_period("M")
                    )
                )
            endpoints = set(pd.to_datetime(pairs.terminal_date).dt.to_period("M"))
            if origin_sets[0] != endpoints or origin_sets[1] != endpoints:
                raise ValueError(
                    f"Origin cohorts differ for {universe},h={shift}: literal-only={origin_sets[0]-endpoints}; endpoint-only={endpoints-origin_sets[0]}; material-only={origin_sets[1]-endpoints}"
                )
            for _, pair in pairs.iterrows():
                origin = pd.Timestamp(pair.terminal_date).to_period("M")
                months = pd.period_range(origin + 1, origin + shift, freq="M")
                history = panel.loc[months]
                initial = _winner(panel.loc[origin].to_dict())[0]
                winners = history.apply(lambda row: _winner(row.to_dict())[0], axis=1)
                changed = winners.ne(initial).to_numpy()
                losses = history.max(axis=1) - history[initial]
                category, material_category = change_return_categories(changed, losses)
                if (
                    initial != pair.initial_winner
                    or winners.iloc[-1] != pair.shifted_window_reported_winner
                    or float(losses.iloc[-1]) != pair.endpoint_loss
                ):
                    raise ValueError("Origin history conflicts with stored endpoint pair")
                for saved, events in ((literal, changed), (material, (losses > 0.0025).to_numpy())):
                    old = saved.loc[
                        pd.to_datetime(saved.origin_date).dt.to_period("M") == origin
                    ].iloc[0]
                    first_by_h = bool(old.event and old.survival_duration_months <= shift)
                    if bool(events.any()) != first_by_h:
                        raise ValueError(
                            "First-failure history does not reproduce the saved survival audit"
                        )
                    if shift == 12 and saved is literal:
                        if bool(old.regained_by_12) != (category == "B"):
                            raise ValueError(
                                "Literal return does not reproduce the saved h=12 audit"
                            )
                records.append(
                    dict(
                        universe=universe,
                        h_months=shift,
                        origin_date=str(origin),
                        initial_winner=initial,
                        winner_at_h=winners.iloc[-1],
                        literal_category=category,
                        material_category=material_category,
                        first_change_within_h=bool(changed.any()),
                        first_gt25_within_h=bool((losses > 0.0025).any()),
                        endpoint_loss_bp=float(losses.iloc[-1] * 10000),
                    )
                )
            group = pd.DataFrame(records).loc[
                lambda x: (x.universe == universe) & (x.h_months == shift)
            ]
            n = len(group)
            row = dict(universe=universe, h_months=shift, n_eligible=n)
            for category in ("A", "B", "C", "A25", "B25", "C25"):
                column = "material_category" if category.endswith("25") else "literal_category"
                count = int((group[column] == category).sum())
                row[f"{category}_count"], row[f"{category}_share"] = count, count / n
            assert row["A_count"] + row["B_count"] + row["C_count"] == n
            assert row["A25_count"] + row["B25_count"] + row["C25_count"] == n
            assert row["B_count"] + row["C_count"] == int(group.first_change_within_h.sum())
            assert row["B25_count"] + row["C25_count"] == int(group.first_gt25_within_h.sum())
            assert row["C_count"] == int(pairs.reported_winner_change.sum())
            assert row["C25_count"] == int((pairs.endpoint_loss > 0.0025).sum())
            for suffix in ("", "25"):
                denominator = row[f"B{suffix}_count"] + row[f"C{suffix}_count"]
                row[f"returned_among_events{suffix}_count"] = row[f"B{suffix}_count"]
                row[f"returned_among_events{suffix}_denominator"] = denominator
                row[f"returned_among_events{suffix}_share"] = (
                    row[f"B{suffix}_count"] / denominator if denominator else np.nan
                )
            summaries.append(row)
            validations.append(
                f"{label}, h={shift}: full-follow-up survival and endpoint origin sets identical ({n} origins); all first-event and fixed-endpoint counts match origin-level outputs."
            )
    summary = pd.DataFrame(summaries)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output / "origins.csv", index=False)
    summary.to_csv(output / "summary.csv", index=False)
    lines = [
        "# Change-and-return: fixed-origin monthly histories",
        "",
        "H=120; December origins with complete h-month follow-up. A = uninterrupted initial-winner identity; B = changed at least once and returned by h; C = displaced at h. A25/B25/C25 use strict loss >25 bp as failure and inclusive loss <=25 bp as within tolerance. Recovery is not permanent and the initial method is never reset. Percentages in the first six columns use N; conditional return fractions use first-event counts.",
        "",
        "| Universe | h | N | A | B | C | A25 | B25 | C25 | Returned / first changes | Below threshold again / first >25-bp events |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in summary.iterrows():
        cells = [
            f"{r[f'{c}_count']} ({100*r[f'{c}_share']:.1f}%)"
            for c in ("A", "B", "C", "A25", "B25", "C25")
        ]
        conditional = [
            f"{r[f'returned_among_events{s}_count']}/{r[f'returned_among_events{s}_denominator']} ({100*r[f'returned_among_events{s}_share']:.1f}%)"
            for s in ("", "25")
        ]
        lines.append(
            f"| {r.universe} | {r.h_months} | {r.n_eligible} | "
            + " | ".join(cells + conditional)
            + " |"
        )
    lines += ["", "## Validation", ""] + ["- " + v for v in validations]
    lines += [
        "",
        "No aggregate subtraction was used to infer recovery: every category was built from each origin's monthly winner identities and CEQs. C and C25 reproduce the endpoint counts on exactly the same origins; B+C and B25+C25 reproduce first-failure events on those origins. Recent censored origins without complete follow-up are excluded, not scored as uninterrupted persistence. Reported deterministic identities use the frozen five-method order.",
        "",
        "## Interpretation and recommendation",
        "",
        "**Moderately informative; add to supplement.** A meaningful fraction of first failures is no longer present at the fixed later horizon. This explicitly reconciles first-passage durability with endpoint reproducibility, but much of the h=12 recovery evidence already exists in the survival audit. The h=24 origin-level breakdown and explicit conditional denominators add clarity rather than a new inferential claim. Neither a return at h nor a loss back within tolerance implies permanent recovery.",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary



def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    root = parser.parse_args().root
    change_and_return(root, read_frozen(root))

if __name__ == "__main__":
    main()
