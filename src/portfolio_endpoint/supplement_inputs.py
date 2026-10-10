"""Read frozen monthly CEQs and endpoint pairs; no portfolio reconstruction."""
from __future__ import annotations


import numpy as np
import pandas as pd

from .analysis import TIE_BREAK_ORDER

SAMPLES = {
    "17_industries": ("17 U.S. industries", "primary17", "primary_17_definitive_B2000"),
    "14_countries": ("14 developed-country markets", "countries", "country_replication_B1000"),
}
ATOL = 1e-12


def saved_monthly_panel(path):
    """Merge persisted endpoint CEQs without estimating any return-window statistic."""
    pairs = pd.read_csv(path, float_precision="round_trip")
    pieces = []
    for prefix in ("earlier", "later"):
        frame = pairs[[f"{prefix}_ceq_{m}" for m in TIE_BREAK_ORDER]].copy()
        frame.columns = list(TIE_BREAK_ORDER)
        frame.index = pd.to_datetime(pairs[f"{prefix}_endpoint"]).dt.to_period("M")
        pieces.append(frame)
    merged = pd.concat(pieces).sort_index()
    for _, group in merged.loc[merged.index.duplicated(keep=False)].groupby(level=0):
        if not (group.to_numpy() == group.iloc[0].to_numpy()).all():
            raise ValueError("Overlapping persisted CEQs disagree")
    panel = merged.loc[~merged.index.duplicated()]
    if not panel.index.equals(pd.period_range(panel.index[0], panel.index[-1], freq="M")):
        raise ValueError("Saved monthly CEQ panel has gaps")
    if not np.isfinite(panel.to_numpy()).all():
        raise ValueError("Saved monthly CEQs contain undefined values")
    return panel


def read_frozen(root):
    audit = pd.read_csv(
        root / "results/gap_perturbation_diagnostic/winner_change_audit_all_pairs.csv",
        float_precision="round_trip",
    )
    inputs = {}
    for universe, (_, prefix, folder) in SAMPLES.items():
        panel = saved_monthly_panel(
            root / f"results/calendar_window_robustness/{universe}_H120_monthly_endpoint_pairs.csv"
        )
        full = audit.loc[
            (audit.universe == universe)
            & (audit["sample"] == "december_full_eligible")
            & (audit.horizon_months == 120)
        ]
        baseline = pd.read_csv(
            root / f"results/{folder}/endpoint_pairs.csv", float_precision="round_trip"
        )
        for shift in (12, 24):
            pairs = full.loc[full.displacement_months == shift].sort_values("terminal_date")
            if pairs.empty or pairs.terminal_date.duplicated().any():
                raise ValueError(f"Missing/duplicate saved h={shift} losses for {universe}")
            if shift == 12:
                if not np.array_equal(
                    pairs.endpoint_loss, baseline.endpoint_loss
                ) or not np.array_equal(pairs.terminal_date, baseline.earlier_endpoint):
                    raise ValueError("Canonical primary pairs do not reproduce exactly")
        inputs[universe] = (panel, full, baseline)
    return inputs
