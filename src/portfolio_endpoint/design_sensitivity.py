"""Bounded, descriptive calendar-phase and evaluation-window checks.

Does not modify baseline artifacts or run bootstrap replications. Cached monthly
net paths are evaluated by the existing frozen endpoint implementation.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER, ceq, endpoint_reproducibility
from .engine import PathResult, run_continuous_path
from .ingest import project_root
from .methods import HEADLINE_METHODS


UNIVERSES = {
    "17_industries": (
        "ff_17_industry_value_weighted_monthly.csv", "primary_17_definitive_B2000"
    ),
    "14_countries": (
        "ff_international_country_markets_usd_monthly.csv", "country_replication_B1000"
    ),
}


def summarize(table: pd.DataFrame) -> dict:
    """Keep strict materiality, integer counts, and unrounded reported rates."""
    n = len(table)
    if not n:
        raise ValueError("No eligible endpoint pairs")
    losses_bp = table.endpoint_loss * 10000
    switches = int(table.literal_switch.sum())
    # Compare in native CEQ units: exactly 25 bp is not material.
    material = int((table.endpoint_loss > 25 / 10000).sum())
    return {
        "n_pairs": n, "switch_count": switches, "switch_rate_pct": 100 * switches / n,
        "loss_gt25_count": material, "loss_gt25_rate_pct": 100 * material / n,
        "mean_loss_ceq_bp": float(losses_bp.mean()),
        "median_loss_ceq_bp": float(losses_bp.median()),
        "p90_loss_ceq_bp": float(losses_bp.quantile(.9)),
        "first_terminal_date": str(table.earlier_endpoint.min().date()),
        "last_terminal_date": str(table.earlier_endpoint.max().date()),
    }


def net_only_paths(matrix: pd.DataFrame) -> dict[str, PathResult]:
    """Adapter to the frozen evaluator; unused holdings fields stay empty.

These are not newly initialized portfolios. Each net series is the full,
already cost-adjusted continuous stream; the evaluator reads only net_returns.
"""
    return {name: PathResult(pd.DataFrame(), pd.Series(dtype=float), matrix[name],
                             pd.Series(dtype=float)) for name in TIE_BREAK_ORDER}


def evaluate(matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    periods = matrix.index.to_period("M")
    if not periods.equals(pd.period_range(periods[0], periods[-1], freq="M")):
        raise ValueError("Paths must have one uninterrupted observation per month")
    if not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("Paths contain nonfinite returns")
    paths = net_only_paths(matrix)
    tables = {}
    for horizon in (120, 60):
        table = endpoint_reproducibility(paths, horizon, 12, 5, december_only=False)
        # Independently verify every slice length, displacement, and saved score.
        for row in table.itertuples(index=False):
            pos = matrix.index.get_loc(row.earlier_endpoint)
            later = matrix.index.get_loc(row.later_endpoint)
            assert later - pos == 12
            assert periods[later].ordinal - periods[pos].ordinal == 12
            for prefix, end in (("earlier", pos), ("later", later)):
                window = matrix.iloc[end - horizon + 1:end + 1]
                assert len(window) == horizon
                for method in TIE_BREAK_ORDER:
                    assert ceq(window[method], 5) == getattr(row, f"{prefix}_ceq_{method}")
        tables[horizon] = table
    phases = pd.DataFrame([
        {"terminal_month": month, "month_name": calendar.month_abbr[month],
         "H_months": 120, "h_months": 12,
         **summarize(tables[120].loc[tables[120].earlier_endpoint.dt.month == month])}
        for month in range(1, 13)
    ])
    december = {h: t.loc[t.earlier_endpoint.dt.month == 12].copy()
                for h, t in tables.items()}
    common = set(december[60].earlier_endpoint) & set(december[120].earlier_endpoint)
    window_rows = []
    for comparison in ("all_eligible", "common_dates"):
        for horizon in (120, 60):
            selected = december[horizon]
            if comparison == "common_dates":
                selected = selected.loc[selected.earlier_endpoint.isin(common)]
            window_rows.append({"comparison_set": comparison, "H_months": horizon,
                                "h_months": 12, **summarize(selected)})
    return phases, pd.DataFrame(window_rows), tables


def baseline_check(table: pd.DataFrame, original: Path, universe: str) -> None:
    december = table.loc[table.earlier_endpoint.dt.month == 12].reset_index(drop=True)
    saved = pd.read_csv(original, parse_dates=["earlier_endpoint", "later_endpoint"])
    assert len(december) == len(saved)
    for name in saved.columns:
        if pd.api.types.is_numeric_dtype(saved[name]) and saved[name].dtype != bool:
            np.testing.assert_allclose(december[name], saved[name], rtol=0, atol=1e-12)
        else:
            pd.testing.assert_series_equal(december[name], saved[name], check_names=False)
    if universe == "17_industries":
        result = summarize(december)
        assert (result["n_pairs"], result["switch_count"], result["loss_gt25_count"]) == (84, 18, 5)
        assert f'{result["switch_rate_pct"]:.1f}' == "21.4"
        assert f'{result["loss_gt25_rate_pct"]:.1f}' == "6.0"
        assert f'{result["mean_loss_ceq_bp"]:.2f}' == "7.35"


def paths_once(root: Path, output: Path, universe: str, filename: str) -> pd.DataFrame:
    import scipy
    import sklearn
    source = root / "data/processed" / filename
    identity = {
        "data_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "engine_sha256": hashlib.sha256(Path(__file__).with_name("engine.py").read_bytes()).hexdigest(),
        "methods_sha256": hashlib.sha256(Path(__file__).with_name("methods.py").read_bytes()).hexdigest(),
        "numpy": np.__version__, "pandas": pd.__version__,
        "scipy": scipy.__version__, "sklearn": sklearn.__version__,
        "lookback": 60, "cost": .0025, "rebalance_every": 1,
    }
    cache = output / f"{universe}_continuous_net_returns.csv"
    metadata = output / f"{universe}_path_cache.json"
    if cache.exists():
        if json.loads(metadata.read_text()) != identity:
            raise ValueError("Cached paths differ in data/code/environment; do not silently overwrite")
        return pd.read_csv(cache, index_col="date", parse_dates=True, float_precision="round_trip")
    returns = pd.read_csv(source, index_col="date", parse_dates=True)
    print(f"Reconstructing {universe}: five frozen paths once", flush=True)
    streams = {}
    for name in TIE_BREAK_ORDER:
        streams[name] = run_continuous_path(returns, HEADLINE_METHODS[name], 60, .0025, 1).net_returns
    matrix = pd.DataFrame(streams)
    matrix.index.name = "date"
    matrix.to_csv(cache)
    metadata.write_text(json.dumps(identity, indent=2), encoding="utf-8")
    return matrix


def phase_report(phases: pd.DataFrame) -> str:
    lines = ["# Calendar-phase sensitivity", "",
             "Descriptive, separate annual phases; H=120, h=12, gamma=5, cost=25 bp. "
             "Rates are percentages computed directly from integer counts. No pooling or bootstrap.", ""]
    for universe, group in phases.groupby("universe", sort=False):
        lines += [f"## {universe}", "",
                  "| Quantity | Minimum (months) | Maximum (months) | Phase median | December | December rank |",
                  "|---|---|---|---:|---:|---|"]
        for name in ("switch_rate_pct", "loss_gt25_rate_pct", "mean_loss_ceq_bp"):
            values = group[name]
            dec = group.loc[group.terminal_month == 12, name].iloc[0]
            low = ", ".join(group.loc[values == values.min(), "month_name"])
            high = ", ".join(group.loc[values == values.max(), "month_name"])
            ranks = f"{int((values < dec).sum()) + 1}–{int((values <= dec).sum())}"
            lines.append(f"| {name} | {values.min():.3f} ({low}) | {values.max():.3f} ({high}) | "
                         f"{values.median():.3f} | {dec:.3f} | {ranks} / 12 |")
        holds = (group.switch_rate_pct > group.loss_gt25_rate_pct).all()
        lines += ["", "Rank is ascending (1 = lowest); ranges explicitly show tied ranks.",
                  f"Eligible pairs vary from {group.n_pairs.min()} to {group.n_pairs.max()}. "
                  f"Literal changes exceed >25-bp losses in all twelve phases: {bool(holds)}.", ""]
    return "\n".join(lines)


def window_report(windows: pd.DataFrame, inventory: dict) -> str:
    lines = ["# Evaluation-window sensitivity", "",
             "Descriptive December terminal dates, h=12, gamma=5, cost=25 bp. "
             "H changes only evaluation slices, never the 60-month estimation window or holdings.", ""]
    for universe, group in windows.groupby("universe", sort=False):
        lines += [f"## {universe}", "",
                  "| Sample | H | n | Changes (%) | Loss >25 bp (%) | Mean (CEQ bp) | Median | P90 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for row in group.itertuples():
            lines.append(f"| {row.comparison_set} | {row.H_months} | {row.n_pairs} | "
                         f"{row.switch_count} ({row.switch_rate_pct:.3f}) | "
                         f"{row.loss_gt25_count} ({row.loss_gt25_rate_pct:.3f}) | "
                         f"{row.mean_loss_ceq_bp:.3f} | {row.median_loss_ceq_bp:.3f} | {row.p90_loss_ceq_bp:.3f} |")
        lines.append("")
        for comparison, subset in group.groupby("comparison_set", sort=False):
            short = subset.loc[subset.H_months == 60].iloc[0]
            long = subset.loc[subset.H_months == 120].iloc[0]
            lines.append(f"{comparison}, H60 minus H120: literal changes "
                         f"{short.switch_rate_pct-long.switch_rate_pct:+.3f} percentage points; "
                         f">25-bp losses {short.loss_gt25_rate_pct-long.loss_gt25_rate_pct:+.3f} points; "
                         f"mean loss {short.mean_loss_ceq_bp-long.mean_loss_ceq_bp:+.3f} CEQ bp. "
                         f"Ordinal-versus-economic separation survives: "
                         f"{short.switch_rate_pct > short.loss_gt25_rate_pct}.")
        lines += ["", "Exact coverage dates are in the CSV. The common-date subset is the "
                  "intersection of earlier December terminal dates, not a restriction on estimation history.", ""]
    lines += ["## Existing bootstrap artifact availability", "",
              "No bootstrap was launched. The primary enhanced B=2,000 file already contains H5 "
              "(H=60) replication statistics and paired H5-minus-baseline statistics. "
              "Mean/median/P90 loss and literal switching can be reused without rebuilding any paths. "
              "Only reading these columns and computing summaries would be needed (negligible relative "
              "to portfolio reconstruction). They are all-eligible December statistics, not common-date statistics.", "",
              "Neither run saves replication-level monthly returns or endpoint-level losses. "
              "Strict >25-bp rates and common-date H60 statistics cannot be recovered from the saved "
              "aggregate metrics. The country B=1,000 file has no H5 columns. For those missing "
              "bootstrap quantities, saved seeds/input data/code can reproduce draws, but each draw's "
              "continuous portfolio paths must be regenerated: broadly the same dominant computation "
              "as the existing bootstrap, with some post-processing avoidable. This is not a cheap "
              "window-only recalculation from saved replication paths.", "",
              "Artifact inventory (including exact available columns): `bootstrap_artifact_inventory.json`.", ""]
    for universe, artifact in inventory.items():
        lines.append(f"- {universe}: `{artifact['artifact']}`, "
                     f"B={artifact['replications']}, {len(artifact['H60_columns'])} "
                     "saved H60 / paired-difference columns.")
    return "\n".join(lines)


def main() -> None:
    root = project_root()
    output = root / "results/calendar_window_robustness"
    output.mkdir(parents=True, exist_ok=True)
    phases, windows, provenance, inventory = [], [], {}, {}
    for universe, (filename, run_name) in UNIVERSES.items():
        matrix = paths_once(root, output, universe, filename)
        # Baseline gate BEFORE calculating either new sensitivity.
        baseline = endpoint_reproducibility(net_only_paths(matrix), 120, 12, 5)
        baseline_check(baseline, root / "results" / run_name / "endpoint_pairs.csv", universe)
        print(f"{universe}: baseline gate passed", flush=True)
        phase, window, pairs = evaluate(matrix)
        repeated_matrix = pd.read_csv(output / f"{universe}_continuous_net_returns.csv",
                                     index_col="date", parse_dates=True, float_precision="round_trip")
        pd.testing.assert_frame_equal(matrix, repeated_matrix, check_freq=False)
        phase2, window2, pairs2 = evaluate(repeated_matrix)
        pd.testing.assert_frame_equal(phase, phase2)
        pd.testing.assert_frame_equal(window, window2)
        for horizon in pairs:
            pd.testing.assert_frame_equal(pairs[horizon], pairs2[horizon])
            pairs[horizon].to_csv(output / f"{universe}_H{horizon}_monthly_endpoint_pairs.csv", index=False)
        phase.insert(0, "universe", universe)
        window.insert(0, "universe", universe)
        phases.append(phase)
        windows.append(window)
        draw_file = root / "results" / run_name / "outer_bootstrap.csv"
        draws = pd.read_csv(draw_file)
        inventory[universe] = {
            "artifact": str(draw_file.relative_to(root)), "replications": len(draws),
            "H60_columns": [c for c in draws if c.startswith(("H5_", "delta_H5_"))],
            "monthly_replication_paths_saved": False,
        }
        provenance[universe] = {
            "baseline_endpoint_artifact": f"results/{run_name}/endpoint_pairs.csv",
            "data": f"data/processed/{filename}", "oos_months": len(matrix),
            "baseline_reproduced": True, "two_runs_exactly_equal": True,
            "baseline_statistics": summarize(baseline),
        }
    phase_table, window_table = pd.concat(phases), pd.concat(windows)
    phase_table.to_csv(output / "calendar_phase_sensitivity.csv", index=False)
    window_table.to_csv(output / "evaluation_window_sensitivity.csv", index=False)
    (output / "bootstrap_artifact_inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    (output / "validation.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    (output / "CALENDAR_PHASE_SENSITIVITY.md").write_text(phase_report(phase_table), encoding="utf-8")
    (output / "EVALUATION_WINDOW_SENSITIVITY.md").write_text(window_report(window_table, inventory), encoding="utf-8")
    print(f"Finished: {output}", flush=True)


if __name__ == "__main__":
    main()
