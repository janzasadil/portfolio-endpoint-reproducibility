"""Deterministically extract post-referee quantities from frozen run outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .bootstrap import corrected_pw_stationary_block_length, protocol_block_length
from .ingest import project_root

METHODS = ["equal_weight", "sample_gmv", "ledoit_wolf_gmv", "inverse_volatility", "erc"]
UNIVERSES = {
    "17_industries": ("primary_17_definitive_B2000", "ff_17_industry_value_weighted_monthly.csv"),
    "14_countries": ("country_replication_B1000", "ff_international_country_markets_usd_monthly.csv"),
    "30_industries": ("replication_30_B1000", "ff_30_industry_value_weighted_monthly.csv"),
}


def _bp(value: float) -> float:
    return round(10000.0 * float(value), 2)


def _pct(value: float) -> float:
    return round(100.0 * float(value), 1)


def _ties(row: pd.Series, prefix: str) -> list[str]:
    values = row[[f"{prefix}{m}" for m in METHODS]].to_numpy(dtype=float)
    maximum = values.max()
    return [method for method, value in zip(METHODS, values) if value == maximum]


def _universe_audit(root: Path, name: str, run_dir: str, processed: str) -> tuple[dict, list[dict]]:
    pairs = pd.read_csv(root / "results" / run_dir / "endpoint_pairs.csv")
    losses = pairs.endpoint_loss.astype(float)
    switches = pairs.literal_switch.astype(bool)
    switched = pairs.loc[switches].copy()
    origin_ties = pairs.apply(lambda row: _ties(row, "earlier_ceq_"), axis=1)
    displaced_ties = pairs.apply(lambda row: _ties(row, "later_ceq_"), axis=1)
    zero_switches = switched.loc[switched.endpoint_loss == 0.0].copy()
    zero_details = []
    for index, row in zero_switches.iterrows():
        zero_details.append({
            "origin_date": row.earlier_endpoint,
            "displaced_date": row.later_endpoint,
            "original_winner": row.earlier_winner,
            "reported_displaced_winner": row.later_winner,
            "origin_co_maximizers": origin_ties.loc[index],
            "displaced_co_maximizers": displaced_ties.loc[index],
        })
    nonswitch_nonzero = int(((~switches) & (losses != 0.0)).sum())
    positive = losses[losses > 0.0]
    origin_ceq = pairs[[f"earlier_ceq_{method}" for method in METHODS]].to_numpy(dtype=float)
    sorted_origin_ceq = np.sort(origin_ceq, axis=1)
    gaps = sorted_origin_ceq[:, -1] - sorted_origin_ceq[:, -2]
    raw = pd.read_csv(root / "data" / "processed" / processed, index_col="date")
    observed_blocks = sorted(pd.read_csv(root / "results" / run_dir / "outer_bootstrap.csv", usecols=["block_length"]).block_length.unique().tolist())
    values = raw.to_numpy(dtype=float)
    ew = values.mean(axis=1)
    raw_ew = corrected_pw_stationary_block_length(ew)
    raw_sq = corrected_pw_stationary_block_length((ew - ew.mean()) ** 2)
    block = protocol_block_length(values)
    metrics = {
        "universe": name,
        "eligible_pairs": int(len(pairs)),
        "literal_switch_count": int(switches.sum()),
        "literal_switch_rate_pct": _pct(switches.mean()),
        "loss_gt_25bp_count": int((losses > 0.0025).sum()),
        "loss_gt_25bp_rate_pct": _pct((losses > 0.0025).mean()),
        "unconditional_mean_loss_bp": _bp(losses.mean()),
        "unconditional_p90_loss_bp": _bp(losses.quantile(.9)),
        "switch_n": int(len(switched)),
        "switch_mean_loss_bp": _bp(switched.endpoint_loss.mean()) if len(switched) else None,
        "switch_median_loss_bp": _bp(switched.endpoint_loss.median()) if len(switched) else None,
        "switch_p75_loss_bp": _bp(switched.endpoint_loss.quantile(.75)) if len(switched) else None,
        "switch_p90_loss_bp": _bp(switched.endpoint_loss.quantile(.9)) if len(switched) else None,
        "switch_min_loss_bp": _bp(switched.endpoint_loss.min()) if len(switched) else None,
        "switch_max_loss_bp": _bp(switched.endpoint_loss.max()) if len(switched) else None,
        "switch_zero_loss_count": int((switched.endpoint_loss == 0.0).sum()),
        "switch_positive_loss_count": int((switched.endpoint_loss > 0.0).sum()),
        "switch_loss_gt_25bp_count": int((switched.endpoint_loss > 0.0025).sum()),
        "switch_loss_gt_25bp_share_pct": _pct((switched.endpoint_loss > 0.0025).mean()) if len(switched) else None,
        "origin_exact_max_ties": int(sum(len(value) > 1 for value in origin_ties)),
        "displaced_exact_max_ties": int(sum(len(value) > 1 for value in displaced_ties)),
        "nonswitch_nonzero_loss_count": nonswitch_nonzero,
        "smallest_positive_loss_bp": _bp(positive.min()) if len(positive) else None,
        "zero_loss_switch_details": zero_details,
        "floating_gap_lt_1e12": int((gaps < 1e-12).sum()),
        "floating_gap_lt_1e10": int((gaps < 1e-10).sum()),
        "block_length": {"T": int(len(raw)), "equal_weight_selector": int(raw_ew), "squared_demeaned_selector": int(raw_sq), "final_expected_block_length": int(block), "observed_block_lengths_in_final_draws": observed_blocks, "held_fixed_across_replications": observed_blocks == [int(block)], "module": "portfolio_endpoint.bootstrap", "function": "protocol_block_length / corrected_pw_stationary_block_length", "package_versions": {"numpy": np.__version__, "pandas": pd.__version__}},
    }
    tidy = [{"universe": name, "statistic": key, "value": value} for key, value in metrics.items() if key not in {"zero_loss_switch_details", "block_length"}]
    tidy += [{"universe": name, "statistic": f"block_{key}", "value": value} for key, value in metrics["block_length"].items() if not isinstance(value, dict)]
    return metrics, tidy


def main() -> None:
    root = project_root(); output = root / "results" / "post_referee"; output.mkdir(parents=True, exist_ok=True)
    metrics, rows = {}, []
    for name, (run_dir, processed) in UNIVERSES.items():
        item, tidy = _universe_audit(root, name, run_dir, processed)
        metrics[name] = item; rows.extend(tidy)
    (output / "post_referee_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf8")
    pd.DataFrame(rows).to_csv(output / "post_referee_metrics.csv", index=False)
    audit = ["# Post-referee extraction audit", "", "## Sources", "", "- Frozen `endpoint_pairs.csv` and `outer_bootstrap.csv` from the 17-industry, 14-country, and 30-industry final runs.", "- Exact processed monthly return histories under `data/processed/` for deterministic block-length reconstruction.", "- `portfolio_endpoint.bootstrap.protocol_block_length` and `corrected_pw_stationary_block_length`.", "", "## Design preservation", "", "No scientific specification, universe, threshold, or inference procedure was changed. No bootstrap was rerun. Block lengths were deterministically reconstructed because final manifests do not record component selector values, then confirmed against the fixed block-length column in every saved bootstrap draw.", "", "## Headline-count verification", ""]
    for name in ("17_industries", "14_countries"):
        m = metrics[name]; audit.append(f"- {name}: {m['eligible_pairs']} pairs; {m['literal_switch_count']} switches ({m['literal_switch_rate_pct']}%); {m['loss_gt_25bp_count']} losses >25 bp ({m['loss_gt_25bp_rate_pct']}%).")
    (output / "post_referee_extraction_audit.md").write_text("\n".join(audit) + "\n", encoding="utf8")
    for name in ("17_industries", "14_countries"):
        m = metrics[name]; print(f"### {name.replace('_', ' ')}\n- switch rate: {m['literal_switch_rate_pct']}%\n- loss >25 bp rate: {m['loss_gt_25bp_rate_pct']}%\n- mean loss | switch: {m['switch_mean_loss_bp']} bp\n- median loss | switch: {m['switch_median_loss_bp']} bp\n- zero-loss switches / switches: {m['switch_zero_loss_count']}/{m['switch_n']}\n- exact max-tie count at origins: {m['origin_exact_max_ties']}\n- exact max-tie count at displaced windows: {m['displaced_exact_max_ties']}\n- final stationary-bootstrap expected block length: {m['block_length']['final_expected_block_length']}")
    print(f"### 30 industries\n- final stationary-bootstrap expected block length: {metrics['30_industries']['block_length']['final_expected_block_length']}")


if __name__ == "__main__":
    main()
