"""Rebuild every paper analysis from raw data, including all registered bootstrap runs."""

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

from .ingest import ingest_dataset, project_root, sha256
from .provenance import manifest_target

METADATA = (
    "pyproject.toml", "requirements-frozen.txt", "config/paper_design.yaml",
    "replication/frozen_run_registry.json", "replication/data_manifest.json",
    "replication/publication_inputs.json", "replication/qf_reference_table_bodies.json",
    "replication/reference_outputs.json",
)


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def analysis_plan(root):
    registry = json.loads((root / "replication/frozen_run_registry.json").read_text())
    plan = []
    for name, run in registry.items():
        plan.append({"name": name, "dataset": run["dataset"],
                     "replications": run["resolved_study"]["outer_bootstrap_replications"],
                     "seed": run["resolved_study"]["bootstrap_seed"],
                     "lookback": run["resolved_study"]["estimation_window_months"],
                     "rebalance_every": run["rebalance_every"],
                     "enhanced": run["enhanced_sensitivities"],
                     "fixed_block_length": run["fixed_block_length"]})
    return plan


def study_arguments(work, run):
    arguments = ["--root", str(work), "--dataset", run["dataset"], "--run-name", run["name"],
                 "--lookback", str(run["lookback"]), "--rebalance-every", str(run["rebalance_every"])]
    if run["enhanced"]:
        arguments.append("--enhanced-sensitivities")
    if run["fixed_block_length"] is not None:
        arguments += ["--fixed-block-length", str(run["fixed_block_length"])]
    folder = work / "results" / run["name"]
    if folder.exists() and any(folder.iterdir()):
        draws = folder / "outer_bootstrap.csv"
        if not draws.exists():
            raise ValueError(f"Incomplete non-checkpointed study {run['name']}; use a fresh output directory")
        completed = len(pd.read_csv(draws, usecols=["replication"]))
        remaining = run["replications"] - completed
        if remaining < 0:
            raise ValueError("Checkpoint exceeds the registered replication count")
        arguments += ["--resume"]
        if remaining == 0:
            arguments += ["--finalize"]
        else:
            arguments += ["--outer-reps", str(remaining)]
    else:
        arguments += ["--outer-reps", str(run["replications"])]
    return arguments


def raw_identity(root, work, plan):
    import numpy, scipy, sklearn
    return {"plan": plan,
            "metadata": {name: sha256(root / name) for name in METADATA},
            "source": {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
            "layouts": {p.name: sha256(p) for p in sorted((root / "generated").glob("table_*.tex"))},
            "raw": {p.name: sha256(p) for p in sorted((work / "data/raw").glob("*.zip"))},
            "processed": {p.name: sha256(p) for p in sorted((work / "data/processed").glob("*.csv"))},
            "environment": {"python": sys.version, "platform": platform.platform(),
                            "numpy": numpy.__version__, "pandas": pd.__version__,
                            "scipy": scipy.__version__, "sklearn": sklearn.__version__}}


def output_hashes(work, directory):
    return {p.relative_to(work).as_posix(): sha256(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def full_reproduction(root, work, *, raw_dir=None, resume=False, require_paper_data=False, smoke=False):
    """Only code/config/layout references come from root; no saved analysis is copied."""
    root, work = project_root(root), Path(work).resolve()
    plan = analysis_plan(root)
    if smoke:
        plan = [{**run, "replications": min(run["replications"], 1)} for run in plan]
    config = yaml.safe_load((root / "config/paper_design.yaml").read_text())
    if any(run["seed"] != config["study"]["bootstrap_seed"] for run in plan):
        raise ValueError("Configured bootstrap seed differs from the executed run registry")
    state_path = work / "ANALYSIS_STATE.json"
    if work.exists():
        if not resume or not state_path.is_file():
            raise FileExistsError("Choose a fresh output directory, or --resume a checkpointed full analysis")
        state = json.loads(state_path.read_text())
    else:
        if resume:
            raise ValueError("Resume requires an existing full-analysis directory")
        work.mkdir(parents=True)
        for name in METADATA:
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
        (work / "generated").mkdir()
        for source in (root / "generated").glob("table_*.tex"):
            shutil.copyfile(source, work / "generated" / source.name)
        state = {"identity": None, "completed": {}}
        write_json(state_path, state)
    if state["identity"] is None:
        for name, spec in config["datasets"].items():
            if raw_dir is not None:
                source = Path(raw_dir) / spec["raw_file"]
                target = work / "data/raw" / spec["raw_file"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            print(f"Ingesting {name}: raw data -> fixed paper sample", flush=True)
            ingest_dataset(name, spec, work)
        state["identity"] = raw_identity(root, work, plan)
        write_json(state_path, state)
    elif state["identity"] != raw_identity(root, work, plan):
        raise ValueError("Full-analysis resume identity changed; inputs, code, layout, environment and design must match")
    # Check copied configuration as well as originals before resuming any scientific stage.
    for name, digest in state["identity"]["metadata"].items():
        if sha256(work / name) != digest:
            raise ValueError("Working metadata changed: " + name)
    vintage = json.loads((root / "replication/data_manifest.json").read_text())
    matching = {name: sha256(work / spec["processed_file"]) == spec["processed_sha256"]
                for name, spec in vintage.items()}
    print("Paper-vintage processed data match:", matching, flush=True)
    if require_paper_data and not all(matching.values()):
        raise ValueError("Downloaded data differ from paper vintage; see recorded raw/processed hashes")

    def assert_identity():
        if state["identity"] != raw_identity(root, work, plan):
            raise ValueError("Full-analysis inputs, code or environment changed during the run")
        if any(sha256(work / name) != digest for name, digest in state["identity"]["metadata"].items()):
            raise ValueError("Working metadata changed during the run")

    def stage(name, directory, action, *, restart_partial=False):
        assert_identity()
        if name in state["completed"]:
            if output_hashes(work, directory) != state["completed"][name]:
                raise ValueError("Completed stage outputs changed: " + name)
            print(f"Verified completed stage: {name}", flush=True)
            return
        if restart_partial and directory.exists():
            # Preserve failed derived output before retrying; bootstrap checkpoints stay in place.
            destination = work / "incomplete" / name
            if work not in directory.resolve().parents or work not in destination.resolve().parents:
                raise ValueError("Incomplete-stage path escapes the working tree")
            suffix = 1
            while destination.exists():
                destination = work / "incomplete" / f"{name}_{suffix}"
                suffix += 1
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(directory), str(destination))
        print(f"Running stage: {name}", flush=True)
        action()
        assert_identity()
        state["completed"][name] = output_hashes(work, directory)
        write_json(state_path, state)

    from . import study, diagnostics, extension, design_sensitivity, gap_perturbation
    for run in plan:
        directory = work / "results" / run["name"]
        stage(run["name"], directory,
              lambda run=run: study.main(study_arguments(work, run)),
              restart_partial=not (directory / "outer_bootstrap.csv").exists())
    stage("diagnostics", work / "results/diagnostics", lambda: diagnostics.run_diagnostics(root=work), restart_partial=True)
    stage("extension", work / "results/extension", lambda: extension.main(["--root", str(work)]), restart_partial=True)
    stage("calendar_window", work / "results/calendar_window_robustness", lambda: design_sensitivity.run(work), restart_partial=True)
    stage("gap_perturbation", work / "results/gap_perturbation_diagnostic",
          lambda: gap_perturbation.run(work, work / "results/gap_perturbation_diagnostic"), restart_partial=True)

    from .qf_publication import assemble
    stage("publication", work / "publication",
          lambda: assemble(work, None, work / "publication", regenerate_figures=True, check_reference=False), restart_partial=True)
    from .publication_validation import validate
    reference_error = None
    try:
        validate(work, work / "publication", check_inputs=False, ignore_provenance=True)
    except ValueError as error:
        reference_error = str(error)
    if not smoke and all(matching.values()) and reference_error is not None:
        raise ValueError("Paper-vintage raw rebuild failed publication comparison: " + reference_error)
    report = {"source": "raw archives; no saved analysis results copied",
              "scope": "pipeline smoke test; not paper inference" if smoke else "complete paper analysis",
              "bootstrap_replications": sum(run["replications"] for run in plan),
              "paper_vintage_data": matching,
              "submitted_tables_match": reference_error is None,
              "reference_difference": reference_error,
              "input_files": {name: sha256(manifest_target(work, name))
                              for name in json.loads((root / "replication/publication_inputs.json").read_text())["files"]}}
    write_json(work / "RAW_REPRODUCTION_REPORT.json", report)
    print(f"Full analysis complete: {work / 'publication'}", flush=True)
    print("Submitted tables match:", report["submitted_tables_match"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--raw-dir", type=Path, help="Use these three raw ZIPs instead of downloading")
    parser.add_argument("--resume", action="store_true", help="Resume with the same code, data and environment")
    parser.add_argument("--require-paper-data", action="store_true", help="Reject revised data before expensive analysis")
    parser.add_argument("--plan", action="store_true", help="Print executed design without downloading or computing")
    parser.add_argument("--smoke", action="store_true", help="QA only: one draw per bootstrap run; not paper results")
    args = parser.parse_args()
    root = project_root(args.root)
    if args.plan:
        print(json.dumps(analysis_plan(root), indent=2))
        return
    default_name = "full_reproduction_smoke" if args.smoke else "full_reproduction"
    full_reproduction(root, args.output_dir or root / "results" / default_name, raw_dir=args.raw_dir,
                      resume=args.resume, require_paper_data=args.require_paper_data, smoke=args.smoke)


if __name__ == "__main__":
    main()
