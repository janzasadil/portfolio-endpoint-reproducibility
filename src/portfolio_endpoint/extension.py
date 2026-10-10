"""Deterministic country replication and bounded extension diagnostics."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from .analysis import (
    TIE_BREAK_ORDER,
    endpoint_reproducibility,
    endpoint_summary,
    ex_ante_selection,
)
from .bootstrap import _paths_at_cost
from .diagnostics import (
    monthly_winner_identities,
    survival_audit_from_winners,
    audit_summary,
    selector_fixed_method_summary,
    displacement_summary,
)
from .engine import run_headline_paths
from .ingest import project_root


def _load_dataset(root, key):
    config = yaml.safe_load((root / "config/paper_design.yaml").read_text())
    settings = config["study"]
    dataset = config["datasets"][key]
    returns = pd.read_csv(
        root / "data/processed" / dataset["processed_file"],
        index_col="date",
        parse_dates=True,
    )
    return returns, settings


def _compute_baseline_statistics(paths, settings):
    """Evaluate the frozen baseline using already-generated portfolio paths."""
    endpoint_pairs = endpoint_reproducibility(
        paths, settings["evaluation_horizon_months"], 12, settings["ceq_risk_aversion"]
    )
    monthly_winners = monthly_winner_identities(
        paths, settings["evaluation_horizon_months"], settings["ceq_risk_aversion"]
    )
    literal_survival = survival_audit_from_winners(monthly_winners)
    material_survival = survival_audit_from_winners(
        monthly_winners, material_threshold=0.0025
    )
    selections = ex_ante_selection(
        paths, settings["evaluation_horizon_months"], settings["ceq_risk_aversion"]
    )
    return (
        endpoint_pairs,
        monthly_winners,
        literal_survival,
        material_survival,
        selections,
    )


def _summarize_by_initial_winner(endpoint_pairs):
    """Summarize endpoint pairs separately for each initial winning method."""
    rows = []
    for method, group in endpoint_pairs.groupby("earlier_winner"):
        rows.append(
            {
                "original_winner": method,
                "n_origins": len(group),
                "switch_frequency": group.literal_switch.mean(),
                "mean_endpoint_loss": group.endpoint_loss.mean(),
                "median_endpoint_loss": group.endpoint_loss.median(),
                "loss_exceeds_25bp": (group.endpoint_loss > 0.0025).mean(),
            }
        )
    return pd.DataFrame(rows)


def _summarize_winner_transitions(endpoint_pairs):
    """Return transition counts and row proportions (not percentages)."""
    counts = pd.crosstab(
        endpoint_pairs.earlier_winner, endpoint_pairs.later_winner
    ).reindex(index=TIE_BREAK_ORDER, columns=TIE_BREAK_ORDER, fill_value=0)
    return counts, counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0)


def _summarize_winner_margins(endpoint_pairs):
    grouped_pairs = endpoint_pairs.assign(
        margin_group=np.where(
            endpoint_pairs.earlier_margin <= 0.0025, "<=25bp", ">25bp"
        )
    )
    margin_summary = (
        grouped_pairs.groupby("margin_group")
        .agg(
            n=("endpoint_loss", "size"),
            mean_margin=("earlier_margin", "mean"),
            switch_frequency=("literal_switch", "mean"),
            mean_endpoint_loss=("endpoint_loss", "mean"),
            loss_exceeds_25bp=("endpoint_loss", lambda x: (x > 0.0025).mean()),
        )
        .reset_index()
    )
    return (
        margin_summary,
        grouped_pairs[
            [
                "earlier_endpoint",
                "earlier_margin",
                "endpoint_loss",
                "literal_switch",
                "margin_group",
            ]
        ],
    )


def _summarize_endpoint_displacements(paths, settings):
    pairs_by_displacement = {
        displacement: endpoint_reproducibility(
            paths,
            settings["evaluation_horizon_months"],
            displacement,
            settings["ceq_risk_aversion"],
        )
        for displacement in (6, 12, 24)
    }
    common_origins = set.intersection(
        *(set(pairs.earlier_endpoint) for pairs in pairs_by_displacement.values())
    )
    rows = []
    for displacement, pairs in pairs_by_displacement.items():
        for sample, sample_pairs in [
            ("full_eligible", pairs),
            (
                "common_calendar_origins",
                pairs[pairs.earlier_endpoint.isin(common_origins)],
            ),
        ]:
            rows.append(
                {
                    "h": displacement,
                    "sample": sample,
                    **displacement_summary(sample_pairs),
                }
            )
    return pd.DataFrame(rows)


def _leave_one_out(returns, settings):
    """Rebuild the frozen portfolio rules after omitting each asset in turn."""
    rows = []
    for asset in returns.columns:
        print(f"Leave-one-out [N={returns.shape[1]}]: omitting {asset}", flush=True)
        paths = run_headline_paths(returns.drop(columns=asset), 60, 0.0025)
        endpoint_pairs, monthly_winners, literal_survival, _, _ = (
            _compute_baseline_statistics(paths, settings)
        )
        rows.append(
            {
                "omitted_asset": asset,
                "n_assets": returns.shape[1] - 1,
                "n_origins": len(endpoint_pairs),
                "mean_endpoint_loss": endpoint_pairs.endpoint_loss.mean(),
                "literal_switch_frequency": endpoint_pairs.literal_switch.mean(),
                "survival_12_complete_followup": audit_summary(literal_survival)[
                    "survival_12_complete_followup"
                ],
            }
        )
    return pd.DataFrame(rows)


def _write_universe_results(
    root, output_dir, prefix, dataset_key, include_leave_one_out
):
    returns, settings = _load_dataset(root, dataset_key)
    paths = run_headline_paths(returns, 60, 0.0025)
    endpoint_pairs, monthly_winners, literal_survival, material_survival, selections = (
        _compute_baseline_statistics(paths, settings)
    )
    endpoint_pairs.to_csv(output_dir / f"{prefix}_endpoint_pairs.csv", index=False)
    literal_survival.to_csv(
        output_dir / f"{prefix}_literal_origin_audit.csv", index=False
    )
    material_survival.to_csv(
        output_dir / f"{prefix}_material25_origin_audit.csv", index=False
    )
    summary = {
        "endpoint": endpoint_summary(endpoint_pairs),
        "literal_survival": audit_summary(literal_survival),
        "material25_survival": audit_summary(material_survival),
        "n_ex_ante_decisions": len(selections),
        "selector": {
            "hit_rate": float(selections.selector_hit.mean()),
            "mean_regret": float(selections.selection_regret.mean()),
            "mean_selector_minus_ensemble": float(
                selections.selector_minus_ensemble.mean()
            ),
            "mean_rank": float(selections.selector_rank.mean()),
        },
    }
    (output_dir / f"{prefix}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf8"
    )
    _summarize_by_initial_winner(endpoint_pairs).to_csv(
        output_dir / f"{prefix}_winner_conditioned.csv", index=False
    )
    transition_counts, transition_proportions = _summarize_winner_transitions(
        endpoint_pairs
    )
    transition_counts.to_csv(output_dir / f"{prefix}_transition_counts.csv")
    transition_proportions.to_csv(output_dir / f"{prefix}_transition_row_percent.csv")
    margin_summary, margin_scatter = _summarize_winner_margins(endpoint_pairs)
    margin_summary.to_csv(output_dir / f"{prefix}_margin_groups.csv", index=False)
    margin_scatter.to_csv(output_dir / f"{prefix}_margin_scatter.csv", index=False)
    _summarize_endpoint_displacements(paths, settings).to_csv(
        output_dir / f"{prefix}_displacement.csv", index=False
    )
    selector_fixed_method_summary(selections).to_csv(
        output_dir / f"{prefix}_selector_fixed.csv", index=False
    )
    if include_leave_one_out:
        _leave_one_out(returns, settings).to_csv(
            output_dir / f"{prefix}_leave_one_out.csv", index=False
        )
    return paths, endpoint_pairs, monthly_winners


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    root = project_root(args.root)
    output_dir = args.output_dir or root / "results/extension"
    output_dir.mkdir(parents=True, exist_ok=True)
    primary_paths, primary_endpoint_pairs, primary_monthly_winners = (
        _write_universe_results(
            root, output_dir, "primary17", "primary_17_industry", True
        )
    )
    country_paths, country_endpoint_pairs, country_monthly_winners = (
        _write_universe_results(
            root, output_dir, "countries", "replication_international_countries", True
        )
    )
    _, settings = _load_dataset(root, "primary_17_industry")
    rows = []
    for label, paths, gamma in [
        ("gamma2", primary_paths, 2),
        ("gamma5", primary_paths, 5),
        ("gamma10", primary_paths, 10),
        ("cost0", _paths_at_cost(primary_paths, 0), 5),
        ("cost25", primary_paths, 5),
        ("cost50", _paths_at_cost(primary_paths, 0.005), 5),
    ]:
        endpoint_pairs = endpoint_reproducibility(paths, 120, 12, gamma)
        monthly_winners = monthly_winner_identities(paths, 120, gamma)
        literal_survival = survival_audit_from_winners(monthly_winners)
        rows.append(
            {
                "setting": label,
                **endpoint_summary(endpoint_pairs),
                "loss_exceeds_25bp_frequency": float(
                    (endpoint_pairs.endpoint_loss > 0.0025).mean()
                ),
                **audit_summary(literal_survival),
            }
        )
    pd.DataFrame(rows).to_csv(
        output_dir / "primary17_gamma_cost_sensitivity.csv", index=False
    )
    rows = []
    for name, monthly_winners in [
        ("primary17", primary_monthly_winners),
        ("countries", country_monthly_winners),
    ]:
        for threshold_bp in (0, 25, 50):
            rows.append(
                {
                    "universe": name,
                    "threshold_bp": threshold_bp,
                    **audit_summary(
                        survival_audit_from_winners(
                            monthly_winners, material_threshold=threshold_bp / 10000
                        )
                    ),
                }
            )
    pd.DataFrame(rows).to_csv(
        output_dir / "materiality_threshold_sensitivity.csv", index=False
    )
    (output_dir / "README.md").write_text(
        "Deterministic extension outputs only. No country bootstrap was run. 17-industry A--D outputs are post-results exploratory; country A--D outputs were prospectively frozen.\n",
        encoding="utf8",
    )
    print(output_dir)


if __name__ == "__main__":
    main()
