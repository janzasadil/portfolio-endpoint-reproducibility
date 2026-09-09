"""Minimal runnable study command for the frozen primary specification."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

from .analysis import (
    ceq_accounting,
    endpoint_reproducibility,
    endpoint_summary,
    ex_ante_selection,
    kaplan_meier,
    survival_summary,
    winner_survival,
)
from .bootstrap import outer_bootstrap, percentile_interval
from .engine import run_headline_paths
from .ingest import project_root


def _json_ready(values: dict) -> dict:
    converted = {}
    for key, value in values.items():
        if isinstance(value, tuple):
            converted[key] = [float(item) for item in value]
        elif isinstance(value, int):
            converted[key] = int(value)
        else:
            converted[key] = float(value)
    return converted


def _run_manifest(root: Path, dataset: str, study: dict, outer_reps: int) -> dict:
    commit = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    import numpy, scipy, sklearn

    return {
        "dataset": dataset,
        "git_commit": commit or "unavailable",
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": numpy.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__,
        "bootstrap_seed": study["bootstrap_seed"], "outer_bootstrap_replications": outer_reps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="primary_17_industry", help="Configured dataset key")
    parser.add_argument("--outer-reps", type=int, default=0, help="Optional outer bootstrap replications")
    args = parser.parse_args()

    root = project_root()
    with (root / "config" / "experiment.yaml").open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    study, dataset = config["study"], config["datasets"][args.dataset]
    returns = pd.read_csv(root / "data" / "processed" / dataset["processed_file"], index_col="date", parse_dates=True)
    paths = run_headline_paths(returns, study["estimation_window_months"], study["transaction_cost_per_half_turnover"])
    endpoints = endpoint_reproducibility(
        paths, study["evaluation_horizon_months"], study["endpoint_displacement_months"], study["ceq_risk_aversion"]
    )
    survival = winner_survival(paths, study["evaluation_horizon_months"], study["ceq_risk_aversion"])
    selections = ex_ante_selection(paths, study["evaluation_horizon_months"], study["ceq_risk_aversion"])

    output_dir = root / "results" / args.dataset
    output_dir.mkdir(parents=True, exist_ok=True)
    endpoints.to_csv(output_dir / "endpoint_pairs.csv", index=False)
    kaplan_meier(survival).to_csv(output_dir / "winner_survival.csv", index=False)
    selections.to_csv(output_dir / "ex_ante_selection.csv", index=False)
    ceq_accounting(paths, study["ceq_risk_aversion"]).to_csv(output_dir / "ceq_accounting.csv", index=False)
    summary = endpoint_summary(endpoints)
    summary.update({
        "mean_selection_regret": float(selections["selection_regret"].mean()),
        "mean_selector_minus_ensemble": float(selections["selector_minus_ensemble"].mean()),
        "selector_hit_rate": float(selections["selector_hit"].mean()),
        "mean_selector_rank": float(selections["selector_rank"].mean()),
        **survival_summary(kaplan_meier(survival)),
    })

    if args.outer_reps:
        bootstrap = outer_bootstrap(
            returns, replications=args.outer_reps, seed=study["bootstrap_seed"],
            lookback=study["estimation_window_months"], transaction_cost=study["transaction_cost_per_half_turnover"],
            horizon=study["evaluation_horizon_months"], displacement=study["endpoint_displacement_months"],
            gamma=study["ceq_risk_aversion"],
        )
        bootstrap.to_csv(output_dir / "outer_bootstrap.csv", index=False)
        summary["outer_bootstrap_replications"] = args.outer_reps
        interval_columns = [
            "mean_endpoint_loss", "literal_switch_frequency", "survival_12_months", "survival_24_months",
            "mean_selection_regret", "mean_selector_minus_ensemble", "selector_hit_rate", "mean_selector_rank",
        ]
        intervals = {name: percentile_interval(bootstrap[name]) for name in interval_columns}
        with (output_dir / "outer_bootstrap_intervals.json").open("w", encoding="utf-8") as handle:
            json.dump({name: list(interval) for name, interval in intervals.items()}, handle, indent=2)
        summary["endpoint_loss_95pct_interval"] = intervals["mean_endpoint_loss"]

    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(_json_ready(summary), handle, indent=2)
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(_run_manifest(root, args.dataset, study, args.outer_reps), handle, indent=2)
    print(json.dumps(_json_ready(summary), indent=2))


if __name__ == "__main__":
    main()
