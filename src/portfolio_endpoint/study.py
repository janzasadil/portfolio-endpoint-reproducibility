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
from .bootstrap import outer_bootstrap, outer_sensitivity_bootstrap, percentile_interval, protocol_block_length
from .engine import run_headline_paths
from .ingest import project_root, sha256


def validate_resume(completed: pd.DataFrame, saved_manifest: dict, identity: dict) -> int:
    """Fail closed for legacy/mixed designs before any output or path is rebuilt."""
    if saved_manifest.get("run_identity") != identity:
        raise ValueError("Resume identity mismatch or legacy manifest: use a new run name; existing outputs preserved")
    if completed.empty or "replication" not in completed:
        raise ValueError("Resume requires a nonempty replication registry")
    if completed.replication.tolist() != list(range(len(completed))):
        raise ValueError("Replication IDs must be unique, ordered, contiguous and start at zero")
    if "block_length" not in completed or not (completed.block_length == identity["block_length"]).all():
        raise ValueError("Saved block lengths differ from the resolved design")
    expected = "baseline_mean_endpoint_loss" if identity["enhanced_sensitivities"] else "mean_endpoint_loss"
    if expected not in completed:
        raise ValueError("Saved replication columns differ from the resolved design")
    return len(completed)


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
    parser.add_argument("--resume", action="store_true", help="Append a bootstrap chunk to an existing run")
    parser.add_argument("--checkpoint-every", type=int, default=10, help="Persist bootstrap draws after this many replications")
    parser.add_argument("--run-name", help="Results subdirectory (default: dataset key)")
    parser.add_argument("--enhanced-sensitivities", action="store_true", help="Emit paired h/H/gamma/cost sensitivity draws")
    parser.add_argument("--lookback", type=int, help="Override the 60-month lookback for a sensitivity run")
    parser.add_argument("--rebalance-every", type=int, default=1, help="Months between rebalances (3 = quarterly)")
    parser.add_argument("--fixed-block-length", type=int, help="Use fixed circular blocks for an outer-bootstrap sensitivity")
    args = parser.parse_args()
    if args.outer_reps < 0 or args.checkpoint_every < 1:
        parser.error("Replication counts must be nonnegative and checkpoint frequency positive")
    if args.fixed_block_length is not None and args.fixed_block_length < 1:
        parser.error("Fixed block length must be positive")
    if args.outer_reps and args.rebalance_every != 1:
        parser.error("Nonmonthly bootstrap is not supported; quarterly runs must be point estimates only")
    if args.enhanced_sensitivities and args.fixed_block_length is not None:
        parser.error("Enhanced sensitivities support stationary resampling only, not fixed blocks")
    if args.resume and not args.outer_reps:
        parser.error("Resume requires positive --outer-reps")

    root = project_root()
    with (root / "config" / "experiment.yaml").open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    study, dataset = config["study"], config["datasets"][args.dataset]
    lookback = args.lookback or study["estimation_window_months"]
    input_path = root / "data" / "processed" / dataset["processed_file"]
    returns = pd.read_csv(input_path, index_col="date", parse_dates=True)
    output_dir = root / "results" / (args.run_name or args.dataset)
    resolved_output = output_dir.resolve()
    if resolved_output == (root / "results").resolve() or (root / "results").resolve() not in resolved_output.parents:
        parser.error("Run name must identify a subdirectory within results")
    manifest = _run_manifest(root, args.dataset, study, 0)
    identity = {
        "dataset": args.dataset, "input_sha256": sha256(input_path),
        "resolved_study": {**study, "estimation_window_months": lookback,
                           "rebalancing_frequency": args.rebalance_every},
        "enhanced_sensitivities": args.enhanced_sensitivities,
        "fixed_block_length": args.fixed_block_length,
        "block_length": (args.fixed_block_length or protocol_block_length(returns.to_numpy())) if args.outer_reps else None,
        "source_sha256": {name: sha256(Path(__file__).with_name(name + ".py"))
                          for name in ("methods", "engine", "analysis", "bootstrap")},
        "environment": {name: manifest[name] for name in ("python", "numpy", "pandas", "scipy", "scikit_learn")},
    }
    # Chunk size and nominal protocol B do not define a draw's identity.
    identity["resolved_study"].pop("outer_bootstrap_replications", None)
    identity["resolved_study"].pop("inner_bootstrap_replications", None)
    completed = pd.DataFrame()
    start_replication = 0
    draw_path = output_dir / "outer_bootstrap.csv"
    if args.resume:
        if not draw_path.exists() or not (output_dir / "run_manifest.json").exists():
            parser.error("Resume requires existing draws and their identity manifest")
        completed = pd.read_csv(draw_path)
        saved_manifest = json.loads((output_dir / "run_manifest.json").read_text())
        start_replication = validate_resume(completed, saved_manifest, identity)
    elif output_dir.exists() and any(output_dir.iterdir()):
        parser.error("Run directory is not empty; choose a new run name or validated --resume")
    manifest["run_identity"] = identity
    manifest["resolved_config"] = {"study": identity["resolved_study"], "dataset": dataset}
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest["outer_bootstrap_replications"] = len(completed)
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    paths = run_headline_paths(returns, lookback, study["transaction_cost_per_half_turnover"], args.rebalance_every)
    endpoints = endpoint_reproducibility(
        paths, study["evaluation_horizon_months"], study["endpoint_displacement_months"], study["ceq_risk_aversion"]
    )
    survival = winner_survival(paths, study["evaluation_horizon_months"], study["ceq_risk_aversion"])
    selections = ex_ante_selection(paths, study["evaluation_horizon_months"], study["ceq_risk_aversion"])

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
        def checkpoint(new_draws: pd.DataFrame) -> None:
            combined = pd.concat([completed, new_draws], ignore_index=True)
            combined.to_csv(draw_path, index=False)
            manifest["outer_bootstrap_replications"] = len(combined)
            (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        common = dict(returns=returns, replications=args.outer_reps, seed=study["bootstrap_seed"],
                      lookback=lookback, transaction_cost=study["transaction_cost_per_half_turnover"],
                      horizon=study["evaluation_horizon_months"], displacement=study["endpoint_displacement_months"],
                      gamma=study["ceq_risk_aversion"], checkpoint_every=args.checkpoint_every,
                      checkpoint_callback=checkpoint)
        bootstrap = (outer_sensitivity_bootstrap(start_replication=start_replication, **common) if args.enhanced_sensitivities
                     else outer_bootstrap(start_replication=start_replication, fixed_block_length=args.fixed_block_length, **common))
        bootstrap = pd.concat([completed, bootstrap], ignore_index=True)
        bootstrap.to_csv(draw_path, index=False)
        summary["outer_bootstrap_replications"] = int(len(bootstrap))
        prefix = "baseline_" if args.enhanced_sensitivities else ""
        interval_columns = [
            f"{prefix}mean_endpoint_loss", f"{prefix}literal_switch_frequency", f"{prefix}survival_12_months", f"{prefix}survival_24_months",
            f"{prefix}mean_selection_regret", f"{prefix}mean_selector_minus_ensemble", f"{prefix}selector_hit_rate", f"{prefix}mean_selector_rank",
        ]
        intervals = {name: percentile_interval(bootstrap[name]) for name in interval_columns}
        with (output_dir / "outer_bootstrap_intervals.json").open("w", encoding="utf-8") as handle:
            json.dump({name: list(interval) for name, interval in intervals.items()}, handle, indent=2)
        summary["endpoint_loss_95pct_interval"] = intervals[f"{prefix}mean_endpoint_loss"]

    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(_json_ready(summary), handle, indent=2)
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as handle:
        manifest["outer_bootstrap_replications"] = int(len(bootstrap)) if args.outer_reps else 0
        json.dump(manifest, handle, indent=2)
    print(json.dumps(_json_ready(summary), indent=2))


if __name__ == "__main__":
    main()
