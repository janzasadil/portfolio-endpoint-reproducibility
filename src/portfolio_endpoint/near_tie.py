"""Extract the frozen near-tie diagnostic from canonical endpoint-pair outputs.

This module intentionally only reads saved endpoint results.  It does not form
portfolios, recompute CEQs, or run bootstrap replications.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER
from .ingest import project_root


UNIVERSES = {
    "17_industries": ("primary_17_definitive_B2000", 84, 18),
    "14_countries": ("country_replication_B1000", 36, 6),
}
MARGIN_CUTOFF = 0.0025


def _ordered_methods(row: pd.Series) -> list[str]:
    """Rank original-endpoint CEQs with the frozen deterministic convention."""
    scores = {method: float(row[f"earlier_ceq_{method}"]) for method in TIE_BREAK_ORDER}
    return sorted(TIE_BREAK_ORDER, key=lambda method: (-scores[method], TIE_BREAK_ORDER.index(method)))


def _pairwise_probability(switch: np.ndarray, nonswitch: np.ndarray) -> tuple[float, int]:
    """Return strict switch-below-nonswitch probability and exact cross-group ties."""
    comparisons = switch[:, None] - nonswitch[None, :]
    return float((comparisons < 0.0).mean()), int((comparisons == 0.0).sum())


def _describe_universe(root: Path, sample: str, run: str, expected_n: int, expected_switches: int) -> tuple[pd.DataFrame, dict]:
    pairs = pd.read_csv(root / "results" / run / "endpoint_pairs.csv")
    if len(pairs) != expected_n:
        raise ValueError(f"{sample}: expected {expected_n} endpoint pairs, found {len(pairs)}")

    rows: list[dict] = []
    for _, row in pairs.iterrows():
        ranking = _ordered_methods(row)
        winner, runner_up = ranking[:2]
        winner_ceq = float(row[f"earlier_ceq_{winner}"])
        runner_up_ceq = float(row[f"earlier_ceq_{runner_up}"])
        margin = winner_ceq - runner_up_ceq
        if winner != row["earlier_winner"]:
            raise ValueError(f"{sample}: original winner conflicts with frozen tie convention")
        if not np.isclose(margin, float(row["earlier_margin"]), rtol=0.0, atol=1e-14):
            raise ValueError(f"{sample}: stored original margin conflicts with original CEQs")
        switch_from_winners = winner != row["later_winner"]
        if bool(row["literal_switch"]) != switch_from_winners:
            raise ValueError(f"{sample}: literal-switch indicator conflicts with endpoint winners")
        if margin < -1e-14:
            raise ValueError(f"{sample}: a computed initial margin is negative")
        rows.append({
            "sample": sample,
            "terminal_date": row["earlier_endpoint"],
            "displaced_terminal_date": row["later_endpoint"],
            "original_winner": winner,
            "original_runner_up": runner_up,
            "winner_ceq": winner_ceq,
            "runner_up_ceq": runner_up_ceq,
            "initial_margin_bp": 10000.0 * margin,
            "literal_switch_h12": bool(row["literal_switch"]),
        })
    terminal = pd.DataFrame(rows)
    switches = terminal.loc[terminal.literal_switch_h12, "initial_margin_bp"].to_numpy(dtype=float)
    nonswitches = terminal.loc[~terminal.literal_switch_h12, "initial_margin_bp"].to_numpy(dtype=float)
    if len(switches) != expected_switches:
        raise ValueError(f"{sample}: expected {expected_switches} literal switches, found {len(switches)}")
    probability, exact_pairwise_ties = _pairwise_probability(switches, nonswitches)
    low = terminal.initial_margin_bp <= 25.0
    split = {
        "margin_le_25bp": {
            "n": int(low.sum()),
            "literal_switches": int(terminal.loc[low, "literal_switch_h12"].sum()),
            "switch_rate": float(terminal.loc[low, "literal_switch_h12"].mean()),
        },
        "margin_gt_25bp": {
            "n": int((~low).sum()),
            "literal_switches": int(terminal.loc[~low, "literal_switch_h12"].sum()),
            "switch_rate": float(terminal.loc[~low, "literal_switch_h12"].mean()),
        },
    }
    summary = {
        "sample": sample,
        "endpoint_pairs": int(len(terminal)),
        "literal_switches": int(len(switches)),
        "literal_nonswitches": int(len(nonswitches)),
        "median_initial_margin_bp": {
            "literal_switches": float(np.median(switches)),
            "literal_nonswitches": float(np.median(nonswitches)),
        },
        "strict_pairwise_probability_switch_margin_lt_nonswitch_margin": probability,
        "exact_cross_group_pairwise_margin_ties": exact_pairwise_ties,
        "initial_margin_nonnegative": bool((terminal.initial_margin_bp >= -1e-10).all()),
        "margin_split_25bp": split,
    }
    return terminal, summary


def _report(summaries: dict[str, dict]) -> str:
    lines = [
        "# Near-tie diagnostic", "",
        "## Scope and source", "",
        "This deterministic exploratory diagnostic reads the frozen `endpoint_pairs.csv` files only. "
        "No portfolio paths, CEQs, or bootstrap replications were recomputed. Initial margins use the original endpoint's five saved CEQs, the frozen tie-break order, and the existing 12-month literal-switch indicator.",
        "",
        "## Primary 17-industry sample", "",
    ]
    for sample in ("17_industries", "14_countries"):
        item = summaries[sample]
        title = "Primary 17-industry sample" if sample == "17_industries" else "Secondary 14-country sample"
        if sample == "14_countries":
            lines += ["", f"## {title}", "", "This secondary descriptive result has only six literal switches.", ""]
        elif lines[-1] != "":
            lines.append("")
        medians = item["median_initial_margin_bp"]
        split = item["margin_split_25bp"]
        lines += [
            f"- Validation: {item['endpoint_pairs']} endpoint pairs; {item['literal_switches']} literal switches; {item['literal_nonswitches']} non-switches; all initial margins non-negative.",
            f"- Median initial margin: {medians['literal_switches']:.2f} CEQ bp for switches and {medians['literal_nonswitches']:.2f} CEQ bp for non-switches.",
            f"- Strict pairwise probability: {item['strict_pairwise_probability_switch_margin_lt_nonswitch_margin']:.4f}. This is the proportion of switch/non-switch pairs where the switching date had the smaller initial margin.",
            f"- Exact cross-group pairwise margin ties: {item['exact_cross_group_pairwise_margin_ties']}.",
            f"- Existing 25-bp split reproduced: <=25 bp: {split['margin_le_25bp']['switch_rate']:.1%} ({split['margin_le_25bp']['literal_switches']}/{split['margin_le_25bp']['n']}); >25 bp: {split['margin_gt_25bp']['switch_rate']:.1%} ({split['margin_gt_25bp']['literal_switches']}/{split['margin_gt_25bp']['n']}).",
        ]
    lines += ["", "## Interpretation boundary", "", "These are descriptive quantities. No confidence intervals, standard errors, p-values, or independence-based tests are reported because annual terminal dates overlap heavily."]
    return "\n".join(lines) + "\n"


def main() -> None:
    root = project_root()
    output = root / "results" / "near_tie_diagnostic"
    output.mkdir(parents=True, exist_ok=True)
    terminals, summaries = [], {}
    for sample, (run, expected_n, expected_switches) in UNIVERSES.items():
        terminal, summary = _describe_universe(root, sample, run, expected_n, expected_switches)
        terminals.append(terminal)
        summaries[sample] = summary
    pd.concat(terminals, ignore_index=True).to_csv(output / "terminal_margin_diagnostic.csv", index=False)
    (output / "near_tie_summary.json").write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf8")
    (output / "near_tie_report.md").write_text(_report(summaries), encoding="utf8")
    primary = summaries["17_industries"]
    print(
        "17 industries: "
        f"{primary['literal_switches']} switches / {primary['endpoint_pairs']} pairs; "
        f"median margins {primary['median_initial_margin_bp']['literal_switches']:.2f} vs "
        f"{primary['median_initial_margin_bp']['literal_nonswitches']:.2f} bp; "
        f"strict pairwise probability {primary['strict_pairwise_probability_switch_margin_lt_nonswitch_margin']:.4f}."
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
