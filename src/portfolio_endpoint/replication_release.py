"""Package frozen local inputs/results; verify a release without downloading data."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from .ingest import project_root, sha256


RUNS = {
    "primary_17_definitive_B2000": ("primary_17_industry", 2000, 60, 1, None, True),
    "country_replication_B1000": ("replication_international_countries", 1000, 60, 1, None, False),
    "replication_30_B1000": ("replication_30_industry", 1000, 60, 1, None, False),
    "primary_17_fixedblock12_B1000": ("primary_17_industry", 1000, 60, 1, 12, False),
    "primary_17_fixedblock24_B1000": ("primary_17_industry", 1000, 60, 1, 24, False),
    "primary_17_L36": ("primary_17_industry", 0, 36, 1, None, False),
    "primary_17_L120": ("primary_17_industry", 0, 120, 1, None, False),
    "primary_17_quarterly": ("primary_17_industry", 0, 60, 3, None, False),
}


def verify(root: Path) -> dict:
    manifest = json.loads((root / "replication/RELEASE_MANIFEST.json").read_text())
    failures = []
    for name, expected in manifest["files"].items():
        target = (root / name).resolve()
        if root.resolve() not in target.parents:
            raise ValueError("Manifest path escapes release root")
        if not target.exists() or sha256(target) != expected:
            failures.append(name)
    if failures:
        raise ValueError(f"Frozen release files missing or changed: {failures}")
    return {"verified_files": len(manifest["files"]), "release": manifest["release"]}


def build(root: Path, source_zip: Path, target: Path) -> None:
    import pandas as pd
    import yaml
    config = yaml.safe_load((root / "config/experiment.yaml").read_text())
    files = {}
    for folder in ("src", "tests", "config", "data/raw", "data/processed"):
        for path in (root / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in ("README.md", "REPLICATION.md", "requirements-frozen.txt", "pyproject.toml",
                 "DATA_MANIFEST.md", "EXECUTION_MANIFEST.md", ".gitignore"):
        files[name] = (root / name).read_bytes()
    for folder in (*RUNS, "diagnostics", "extension", "near_tie_diagnostic", "country_extension"):
        for path in (root / "results" / folder).rglob("*"):
            if path.is_file() and path.suffix in (".csv", ".json", ".md"):
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    files["replication/frozen_source.zip"] = source_zip.read_bytes()
    registry = {}
    for folder, (dataset, count, lookback, rebalance, block, enhanced) in RUNS.items():
        run = root / "results" / folder
        old_manifest = json.loads((run / "run_manifest.json").read_text())
        dataset_config = config["datasets"][dataset]
        input_path = root / "data/processed" / dataset_config["processed_file"]
        raw_path = root / "data/raw" / dataset_config["raw_file"]
        if count:
            draws = pd.read_csv(run / "outer_bootstrap.csv")
            if len(draws) != count or draws.replication.tolist() != list(range(count)):
                raise ValueError(f"Incomplete or invalid frozen replication registry: {folder}")
            selected_lengths = sorted(draws.block_length.unique().tolist())
            if len(selected_lengths) != 1 or (block and selected_lengths != [block]):
                raise ValueError(f"Mixed block rules in {folder}")
        else:
            selected_lengths = []
        study = {**config["study"], "estimation_window_months": lookback,
                 "rebalancing_frequency": "monthly" if rebalance == 1 else "quarterly",
                 "outer_bootstrap_replications": count, "inner_bootstrap_replications": 0}
        registry[folder] = {
            "dataset": dataset, "resolved_study": study,
            "rebalance_every": rebalance, "enhanced_sensitivities": enhanced,
            "bootstrap_scheme": ("fixed_circular" if block else "stationary") if count else "none",
            "fixed_block_length": block, "saved_selected_block_lengths": selected_lengths,
            "data_sha256": sha256(input_path), "raw_sha256": sha256(raw_path),
            "original_run_manifest": old_manifest,
            "provenance_note": "Post-audit resolved registry; original manifests preserved, not retroactively rewritten",
        }
    files["replication/frozen_run_registry.json"] = json.dumps(registry, indent=2).encode()
    manifest = {
        "release": "portfolio-frozen-replication-v2", "date": "2026-10-06",
        "scope": "Frozen inputs and completed outputs; export reproducibility, not a fresh bootstrap verification",
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files["replication/RELEASE_MANIFEST.json"] = json.dumps(manifest, indent=2).encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("Release archive already exists; choose a new filename instead of overwriting")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(name, date_time=(2026, 10, 6, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, data)
    print(json.dumps({"archive": str(target), "sha256": sha256(target), "files": len(files)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path)
    parser.add_argument("--output", type=Path, default=project_root() / "release/portfolio_frozen_replication_v2.zip")
    parser.add_argument("--verify", type=Path, help="Verify an extracted release root instead of building")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify), indent=2))
    elif args.source_zip:
        build(project_root(), args.source_zip, args.output)
    else:
        parser.error("Supply --source-zip to build or --verify to validate")


if __name__ == "__main__":
    main()
