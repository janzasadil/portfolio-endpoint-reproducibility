"""Download, validate, and record Fama--French industry monthly-return panels."""

from __future__ import annotations

import argparse
import hashlib
import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd
import numpy as np
import yaml

MONTHLY_HEADER = "Average Value Weighted Returns -- Monthly"
MISSING_CODES = {-99.99, -999.0}


def validate_monthly_calendar(index: pd.DatetimeIndex) -> None:
    """Rows must represent unique, consecutive month ends, not just row positions."""
    if (len(index) == 0 or index.has_duplicates or not index.is_monotonic_increasing
            or not index.equals(pd.date_range(index[0], index[-1], freq="ME", name=index.name))):
        raise ValueError("Monthly dates must be unique, increasing, uninterrupted month ends")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_value_weighted_monthly(text: str) -> pd.DataFrame:
    """Return a decimal monthly panel from a French-library CSV payload."""
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if MONTHLY_HEADER in line) + 1
    except StopIteration as error:
        raise ValueError("Monthly value-weighted section was not found") from error

    while start < len(lines) and not lines[start].strip():
        start += 1
    end = start + 1
    while end < len(lines) and lines[end].split(",", 1)[0].strip().isdigit():
        end += 1

    if end == start + 1:
        raise ValueError("Monthly value-weighted section contains no observations")
    panel = pd.read_csv(io.StringIO("\n".join(lines[start:end])), index_col=0)
    panel.index = pd.to_datetime(panel.index.astype(str), format="%Y%m") + pd.offsets.MonthEnd(0)
    panel.index.name = "date"
    panel.columns = [column.strip() for column in panel.columns]
    panel = panel.apply(pd.to_numeric, errors="coerce")

    if not np.isfinite(panel.to_numpy()).all() or panel.isin(MISSING_CODES).any().any():
        raise ValueError("Monthly panel contains a missing or French missing-code return")
    validate_monthly_calendar(panel.index)
    return panel / 100.0


def extract_zip_panel(archive: Path) -> pd.DataFrame:
    with zipfile.ZipFile(archive) as compressed:
        csv_names = [name for name in compressed.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in {archive.name}, found {csv_names}")
        return parse_value_weighted_monthly(compressed.read(csv_names[0]).decode("utf-8-sig"))


def append_manifest(manifest: Path, dataset: str, archive: Path, output: Path, panel: pd.DataFrame) -> None:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    record = (
        f"\n| {dataset} | `{archive.name}` → `{output.name}` | {timestamp} | "
        f"raw: `{sha256(archive)}`; processed: `{sha256(output)}` | {panel.shape[0]} × {panel.shape[1]} |\n"
    )
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(record)


def ingest_dataset(name: str, spec: dict[str, str], root: Path) -> None:
    raw_dir, processed_dir = root / "data" / "raw", root / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    archive, output = raw_dir / spec["raw_file"], processed_dir / spec["processed_file"]
    if not archive.exists():
        urlretrieve(spec["url"], archive)
    if spec["raw_file"] == "F-F_International_Countries.zip":
        from .countries import parse_broader_country_markets
        import json
        panel, audit = parse_broader_country_markets(archive)
        audit_dir = root / "results/country_extension"
        audit_dir.mkdir(parents=True, exist_ok=True)
        (audit_dir / "country_data_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    else:
        panel = extract_zip_panel(archive)
    panel.to_csv(output, index=True, float_format="%.10f")
    append_manifest(root / "DATA_MANIFEST.md", name, archive, output, panel)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=project_root() / "config" / "experiment.yaml")
    parser.add_argument("--dataset", action="append", help="Dataset key; may be repeated (default: all)")
    args = parser.parse_args()
    with args.config.open(encoding="utf-8") as handle:
        datasets = yaml.safe_load(handle)["datasets"]
    selected = args.dataset or list(datasets)
    unknown = set(selected) - set(datasets)
    if unknown:
        parser.error(f"Unknown dataset(s): {', '.join(sorted(unknown))}")
    for name in selected:
        ingest_dataset(name, datasets[name], project_root())


if __name__ == "__main__":
    main()
