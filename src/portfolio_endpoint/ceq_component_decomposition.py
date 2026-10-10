"""A7 relative CEQ return/risk components from frozen continuous net paths."""
from __future__ import annotations

from pathlib import Path
from .ingest import project_root

import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER, ceq

from .supplement_inputs import ATOL, SAMPLES, read_frozen

def relative_components(initial_returns, competitor_returns, gamma=5):
    """Relative annualized net-mean and variance-penalty components; ddof=1."""
    initial = np.asarray(initial_returns, dtype=float)
    competitor = np.asarray(competitor_returns, dtype=float)
    if initial.shape != competitor.shape or initial.ndim != 1 or len(initial) < 2:
        raise ValueError("Components need synchronized return windows")
    if not np.isfinite(initial).all() or not np.isfinite(competitor).all():
        raise ValueError("Return windows must be finite")
    return (
        12 * (competitor.mean() - initial.mean()),
        -6 * gamma * (competitor.var(ddof=1) - initial.var(ddof=1)),
    )


def reversal_points(inputs):
    records = []
    for universe, (_, _, baseline) in inputs.items():
        for number, (_, row) in enumerate(
            baseline.loc[baseline.literal_switch].iterrows(), start=1
        ):
            initial, shifted = row.earlier_winner, row.later_winner
            gap = row[f"earlier_ceq_{initial}"] - row[f"earlier_ceq_{shifted}"]
            relative = (row[f"later_ceq_{shifted}"] - row[f"earlier_ceq_{shifted}"]) - (
                row[f"later_ceq_{initial}"] - row[f"earlier_ceq_{initial}"]
            )
            if (
                gap < -ATOL
                or abs((relative - gap) - row.endpoint_loss) > ATOL
                or relative < gap - ATOL
            ):
                raise ValueError("Gap/perturbation identity failure")
            if bool(relative > gap + 0.0025) != bool(row.endpoint_loss > 0.0025):
                raise ValueError("25-bp reference-line classification disagrees")
            records.append(
                dict(
                    universe=universe,
                    point_id=f"{'US' if universe=='17_industries' else 'INT'}{number:02}",
                    endpoint_date=row.earlier_endpoint,
                    shifted_endpoint_date=row.later_endpoint,
                    initial_winner=initial,
                    shifted_winner=shifted,
                    initial_gap_bp=float(gap * 10000),
                    relative_ceq_change_bp=float(relative * 10000),
                    endpoint_loss_bp=float(row.endpoint_loss * 10000),
                    loss_gt25bp=bool(row.endpoint_loss > 0.0025),
                )
            )
    return pd.DataFrame(records)


def return_risk(root, inputs, points, *, output=None):
    output = Path(output) if output is not None else root / "results/return_risk_decomposition"
    records, checks = [], []
    for universe, (_, _, baseline) in inputs.items():
        cache = root / f"results/calendar_window_robustness/{universe}_continuous_net_returns.csv"
        if not cache.exists():
            raise FileNotFoundError(
                f"No saved net return paths: {cache}; do not reconstruct portfolios"
            )
        returns = pd.read_csv(
            cache, index_col="date", parse_dates=True, float_precision="round_trip"
        )
        months = returns.index.to_period("M")
        if (
            not months.equals(pd.period_range(months[0], months[-1], freq="M"))
            or not np.isfinite(returns[list(TIE_BREAK_ORDER)].to_numpy()).all()
        ):
            raise ValueError("Net-return cache incomplete")
        max_residual = 0.0
        # Validate all eligible primary endpoint CEQs, not just the winner changes.
        for _, row in baseline.iterrows():
            for when in ("earlier", "later"):
                pos = returns.index.get_indexer([pd.Timestamp(row[f"{when}_endpoint"])])[0]
                if pos < 119:
                    raise ValueError("No complete saved 120-month return window")
                window = returns.iloc[pos - 119 : pos + 1]
                for method in TIE_BREAK_ORDER:
                    residual = abs(ceq(window[method], 5) - row[f"{when}_ceq_{method}"])
                    max_residual = max(max_residual, residual)
                    if residual > ATOL:
                        raise ValueError("Cached returns do not reproduce frozen net CEQs")
        for _, point in points.loc[points.universe == universe].iterrows():
            components = []
            for date in (point.endpoint_date, point.shifted_endpoint_date):
                pos = returns.index.get_loc(pd.Timestamp(date))
                window = returns.iloc[pos - 119 : pos + 1]
                components.append(
                    relative_components(window[point.initial_winner], window[point.shifted_winner])
                )
            (mu0, risk0), (mu1, risk1) = components
            delta_mu, delta_risk = mu1 - mu0, risk1 - risk0
            delta_residual = (delta_mu + delta_risk) - point.relative_ceq_change_bp / 10000
            loss_residual = (mu1 + risk1) - point.endpoint_loss_bp / 10000
            gap_residual = (mu0 + risk0) + point.initial_gap_bp / 10000
            if max(abs(delta_residual), abs(loss_residual), abs(gap_residual)) > ATOL:
                raise ValueError("Return/risk decomposition does not reproduce CEQ identities")
            pattern = (
                "return_positive_risk_negative"
                if delta_mu > 0 and delta_risk < 0
                else (
                    "risk_positive_return_negative"
                    if delta_risk > 0 and delta_mu < 0
                    else (
                        "both_positive"
                        if delta_mu > 0 and delta_risk > 0
                        else (
                            "both_negative"
                            if delta_mu < 0 and delta_risk < 0
                            else "zero_component_boundary"
                        )
                    )
                )
            )
            records.append(
                dict(
                    **point.to_dict(),
                    initial_mean_component_bp=mu0 * 10000,
                    initial_risk_component_bp=risk0 * 10000,
                    shifted_mean_component_bp=mu1 * 10000,
                    shifted_risk_component_bp=risk1 * 10000,
                    delta_mean_component_bp=delta_mu * 10000,
                    delta_risk_component_bp=delta_risk * 10000,
                    component_pattern=pattern,
                    absolute_mean_component_dominates=abs(delta_mu) > abs(delta_risk),
                    delta_identity_residual=delta_residual,
                    loss_identity_residual=loss_residual,
                    initial_gap_identity_residual=gap_residual,
                )
            )
        checks.append(
            f"{universe}: cached returns reproduce every candidate CEQ at both endpoints of all {len(baseline)} primary pairs; maximum native-unit residual {max_residual:.3g}."
        )
    details = pd.DataFrame(records)
    summaries = []
    for universe in SAMPLES:
        for subset in ("all_winner_changes", "loss_gt25bp"):
            group = details.loc[
                (details.universe == universe)
                & (True if subset == "all_winner_changes" else details.loss_gt25bp)
            ]
            row = dict(universe=universe, subset=subset, n=len(group))
            for component in ("mean", "risk"):
                row[f"delta_{component}_mean_bp"] = float(
                    group[f"delta_{component}_component_bp"].mean()
                )
                row[f"delta_{component}_median_bp"] = float(
                    group[f"delta_{component}_component_bp"].median()
                )
            for pattern in (
                "return_positive_risk_negative",
                "risk_positive_return_negative",
                "both_positive",
                "both_negative",
                "zero_component_boundary",
            ):
                count = int((group.component_pattern == pattern).sum())
                row[f"{pattern}_count"], row[f"{pattern}_share"] = count, count / len(group)
            count = int(group.absolute_mean_component_dominates.sum())
            row["absolute_mean_dominates_count"], row["absolute_mean_dominates_share"] = (
                count,
                count / len(group),
            )
            summaries.append(row)
    summary = pd.DataFrame(summaries)
    output.mkdir(parents=True, exist_ok=True)
    details.to_csv(output / "observations.csv", index=False)
    summary.to_csv(output / "summary.csv", index=False)
    lines = [
        "# Return-versus-risk decomposition of CEQ winner changes",
        "",
        "H=120, h=12, gamma=5; only observed winner-change pairs. Reuse cached continuous NET return paths with frozen within-method costs. No portfolio construction or bootstrap. At both endpoints, Dmu=12(mean_shifted_method-mean_initial_method) and Drisk=-30(var_shifted_method-var_initial_method), with monthly sample variance ddof=1. The shifted method is held fixed in both windows; it is not replaced by each window's best.",
        "",
        "| Universe | Subset | n | Mean delta return | Median delta return | Mean delta risk | Median delta risk | Return + / risk - | Risk + / return - | Both + | Both - | Zero boundary | Absolute return > absolute risk |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in summary.iterrows():
        counts = [
            f"{r[f'{pattern}_count']} ({100*r[f'{pattern}_share']:.1f}%)"
            for pattern in (
                "return_positive_risk_negative",
                "risk_positive_return_negative",
                "both_positive",
                "both_negative",
                "zero_component_boundary",
            )
        ]
        lines.append(
            f"| {r.universe} | {r.subset} | {r.n} | {r.delta_mean_mean_bp:.2f} | {r.delta_mean_median_bp:.2f} | {r.delta_risk_mean_bp:.2f} | {r.delta_risk_median_bp:.2f} | "
            + " | ".join(counts)
            + f" | {r.absolute_mean_dominates_count} ({100*r.absolute_mean_dominates_share:.1f}%) |"
        )
    lines += [
        "",
        "All components are annualized CEQ bp. Exact zero components are a separate boundary category rather than silently assigned a sign. Material-loss subset sizes are reported in the table; small subsets describe individual observations and do not establish reliable population comparisons.",
        "",
        "## Validation and scope",
        "",
    ] + ["- " + c for c in checks]
    lines += [
        "",
        f"Maximum delta identity residual: {details.delta_identity_residual.abs().max():.3g}; maximum shifted loss identity residual: {details.loss_identity_residual.abs().max():.3g}, in native annualized CEQ units. Initial relative component sums also match minus the saved gap. All {len(details)} individual observations, components and residuals remain visible in observations.csv.",
        "",
        "## Interpretation and limitations",
        "",
        "The components describe changes in relative net-return and variance performance, not causal mechanisms or attribution to entering/leaving months. Offsetting components are interpreted using signs and absolute magnitudes, never unstable component/loss contribution ratios.",
        "",
        "Sign patterns, component magnitudes and subset counts above are computed from this run. Conditioning on realized winner changes and the net-return convention limit broader interpretations.",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary, details



def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    root = project_root(parser.parse_args().root)
    inputs = read_frozen(root)
    return_risk(root, inputs, reversal_points(inputs))

if __name__ == "__main__":
    main()
