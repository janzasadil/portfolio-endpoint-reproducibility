"""Download, validate, and record Fama--French industry monthly-return panels."""

from __future__ import annotations

import argparse
import json
import hashlib
import io
import zipfile
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


def project_root(root: Path | None = None) -> Path:
    """Repository-local research tool: explicit root, checkout CWD, or editable source."""
    candidates = [Path(root)] if root is not None else [Path.cwd(), Path(__file__).resolve().parents[2]]
    for candidate in candidates:
        candidate = candidate.resolve()
        if (candidate / "pyproject.toml").is_file() and (candidate / "config/paper_design.yaml").is_file():
            return candidate
    raise ValueError("Run from an editable repository checkout or supply --root CHECKOUT")


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


def write_data_provenance(manifest: Path, dataset: str, archive: Path, output: Path, panel: pd.DataFrame) -> None:
    """Idempotent per-dataset artifact; no timestamp or tracked-document mutation."""
    record = {"dataset": dataset, "raw_file": archive.name, "processed_file": output.name,
              "raw_sha256": sha256(archive), "processed_sha256": sha256(output),
              "rows": panel.shape[0], "columns": list(panel.columns),
              "sample_start": str(panel.index[0].date()), "sample_end": str(panel.index[-1].date())}
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ingest_dataset(name: str, spec: dict[str, str], root: Path) -> None:
    raw_dir, processed_dir = root / "data" / "raw", root / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    archive, output = raw_dir / spec["raw_file"], processed_dir / spec["processed_file"]
    if not archive.exists():
        temporary = archive.with_suffix(archive.suffix + ".download")
        urlretrieve(spec["url"], temporary)
        if not zipfile.is_zipfile(temporary):
            raise ValueError("Downloaded data are not a ZIP archive: " + spec["url"])
        temporary.replace(archive)
    parser_kind = spec.get("parser", "industry_value_weighted")
    if parser_kind == "international_countries":
        from .countries import parse_broader_country_markets
        import json
        panel, audit = parse_broader_country_markets(archive)
        audit_dir = root / "results/country_extension"
        audit_dir.mkdir(parents=True, exist_ok=True)
        (audit_dir / "country_data_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    elif parser_kind == "industry_value_weighted":
        panel = extract_zip_panel(archive)
    else:
        raise ValueError("Unknown dataset parser: " + parser_kind)
    if "sample_start" in spec or "sample_end" in spec:
        panel = panel.loc[spec.get("sample_start"):spec.get("sample_end")]
        expected = pd.date_range(spec["sample_start"], spec["sample_end"], freq="ME", name="date")
        if not panel.index.equals(expected):
            raise ValueError("Raw data do not cover the configured paper sample: " + name)
    if "columns" in spec:
        missing = set(spec["columns"]) - set(panel.columns)
        if missing:
            raise ValueError(f"Raw data missing configured assets: {sorted(missing)}")
        panel = panel.loc[:, spec["columns"]]
    panel.index.name = "date"
    # Match the paper's recorded panel bytes on every operating system.
    panel.to_csv(output, index=True, float_format="%.10f", lineterminator="\r\n")
    write_data_provenance(root / "data/provenance" / (name + ".json"), name, archive, output, panel)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dataset", action="append", help="Dataset key; may be repeated (default: all)")
    args = parser.parse_args()
    root = project_root(args.root)
    config_path = args.config or root / "config/paper_design.yaml"
    with config_path.open(encoding="utf-8") as handle:
        datasets = yaml.safe_load(handle)["datasets"]
    selected = args.dataset or list(datasets)
    unknown = set(selected) - set(datasets)
    if unknown:
        parser.error(f"Unknown dataset(s): {', '.join(sorted(unknown))}")
    for name in selected:
        ingest_dataset(name, datasets[name], root)


if __name__ == "__main__":
    main()
