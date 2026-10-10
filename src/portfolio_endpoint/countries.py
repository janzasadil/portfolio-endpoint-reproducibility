"""Parsing and validation of French international country-market returns."""

from __future__ import annotations

import re
import zipfile
import argparse
import json
from pathlib import Path

import pandas as pd
import numpy as np

from .ingest import project_root, MISSING_CODES, sha256

COUNTRY_NAMES = {
    "Austria": "Austria", "Austrlia": "Australia", "Belgium": "Belgium", "Canada": "Canada",
    "Denmark": "Denmark", "Finland": "Finland", "France": "France", "Germany": "Germany",
    "HongKong": "Hong Kong", "Ireland": "Ireland", "Italy": "Italy", "Japan": "Japan",
    "Malaysia": "Malaysia", "Nethrlnd": "Netherlands", "NewZland": "New Zealand", "Norway": "Norway",
    "Singapor": "Singapore", "Spain": "Spain", "Sweden": "Sweden", "Swtzrlnd": "Switzerland",
    "UK": "Great Britain",
}
SECTION = "Value-Weight Dollar Returns      All 4 Data Items Not Reqd"


def _market_from_text(text: str) -> pd.Series:
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if SECTION in line) + 1
    except StopIteration as error:
        raise ValueError("Broader USD market-return section was not found") from error
    records = []
    started = False
    for line in lines[start:]:
        fields = line.split()
        if not fields or not re.fullmatch(r"\d{6}", fields[0]):
            if started:
                break
            continue
        started = True
        if len(fields) < 2:
            raise ValueError("Malformed country monthly record")
        records.append((fields[0], float(fields[1])))
    if not records:
        raise ValueError("Broader USD market-return section has no monthly observations")
    result = pd.Series([value for _, value in records], index=[date for date, _ in records], dtype=float)
    result.index = pd.to_datetime(result.index, format="%Y%m") + pd.offsets.MonthEnd(0)
    if result.index.has_duplicates or not result.index.is_monotonic_increasing:
        raise ValueError("Country market series has invalid monthly dates")
    if not np.isfinite(result.to_numpy()).all() or result.isin(MISSING_CODES).any():
        raise ValueError("Country market series has missing values or French missing codes")
    return result / 100.0


def parse_broader_country_markets(archive: Path, start: str = "1975-01-31") -> tuple[pd.DataFrame, dict]:
    """Return the balanced broader-USD-Mkt country panel and selection audit."""
    required_start = pd.Timestamp(start)
    with zipfile.ZipFile(archive) as compressed:
        source = {}
        for member in compressed.namelist():
            if not member.endswith(".Dat"):
                continue
            code = Path(member).stem
            if code not in COUNTRY_NAMES:
                raise ValueError(f"Unexpected country file {member}")
            source[COUNTRY_NAMES[code]] = _market_from_text(compressed.read(member).decode("latin1"))
    calendars = {}
    eligible = {}
    for name, series in source.items():
        expected = pd.date_range(required_start, series.index.max(), freq="ME")
        uninterrupted = series.index.min() == required_start and series.index.equals(expected)
        calendars[name] = {"start": str(series.index.min().date()), "end": str(series.index.max().date()),
                           "n_months": len(series), "uninterrupted_from_1975_01": uninterrupted}
        if uninterrupted:
            eligible[name] = series
    if not eligible:
        raise ValueError("No country has uninterrupted data from 1975-01")
    common = pd.concat(eligible, axis=1)
    if common.isna().any().any() or common.index.has_duplicates:
        raise ValueError("Frozen country panel is not complete and synchronized")
    audit = {"source_section": "broader USD value-weighted Mkt; all four data items not required",
             "return_currency": "USD", "selection_rule": "uninterrupted monthly Mkt data from 1975-01",
             "raw_sha256": sha256(archive), "countries": list(common.columns), "n_countries": common.shape[1],
             "sample_start": str(common.index.min().date()), "sample_end": str(common.index.max().date()),
             "n_months": len(common), "all_source_files": calendars}
    return common, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--archive", type=Path, default=Path("data/raw/F-F_International_Countries.zip"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/ff_international_country_markets_usd_monthly.csv"))
    parser.add_argument("--audit", type=Path, default=Path("results/country_extension/country_data_audit.json"))
    args = parser.parse_args()
    root = project_root(args.root)
    for name in ("archive", "output", "audit"):
        value = getattr(args, name)
        if not value.is_absolute():
            setattr(args, name, root / value)
    panel, audit = parse_broader_country_markets(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index_label="date", float_format="%.10f", lineterminator="\r\n")
    args.audit.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), **{key: audit[key] for key in ("n_countries", "n_months", "sample_start", "sample_end")}}, indent=2))


if __name__ == "__main__":
    main()
