"""Prepare and verify a paper-specific local QF replication candidate.

Uses an explicit code/test allowlist and frozen input inventory. No publication,
network access, downloads, simulations or assignment of licensing rights.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

from .ingest import project_root, sha256

MODULES = (
    "__init__",
    "analysis",
    "bootstrap",
    "countries",
    "design_sensitivity",
    "diagnostics",
    "engine",
    "extension",
    "fixed_method_benchmark",
    "gap_perturbation",
    "ingest",
    "methods",
    "qf_figures",
    "qf_publication",
    "qf_tables",
    "qf_release",
    "supplement_inputs",
    "change_return",
    "ceq_component_decomposition",
    "plot_gap_perturbation",
    "study",
)
EXCLUDED_MODULES = (
    "frl_publication",
    "final_publication",
    "near_tie",
    "post_referee",
    "reporting",
    "country_bootstrap_report",
    "replication_release",
)
SCRIPTS = {
    "portfolio-ingest": "ingest",
    "portfolio-study": "study",
    "portfolio-diagnostics": "diagnostics",
    "portfolio-countries": "countries",
    "portfolio-extension": "extension",
    "portfolio-qf-publication": "qf_publication",
}


def manifest_target(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError("Manifest path escapes release root")
    target = (root / name).resolve()
    if root.resolve() not in target.parents:
        raise ValueError("Manifest path escapes release root")
    return target


def verify_manifest(root: Path, manifest: dict) -> dict:
    failures = []
    for name, expected in manifest["files"].items():
        target = manifest_target(root, name)
        if not target.is_file() or sha256(target) != expected:
            failures.append(name)
    if failures:
        raise ValueError(f"Frozen release files missing or changed: {failures}")
    return {
        "verified_files": len(manifest["files"]),
        "release": manifest.get("release", "QF frozen inputs"),
    }


def verify(root: Path) -> dict:
    return verify_manifest(
        root, json.loads((root / "replication/RELEASE_MANIFEST.json").read_text())
    )


def verify_inputs(root: Path) -> dict:
    return verify_manifest(
        root, json.loads((root / "replication/qf_input_manifest.json").read_text())
    )


def assert_dependency_closure(payloads: dict[str, bytes]) -> None:
    """Reject omitted package imports, including function-local legacy imports."""
    available = {
        PurePosixPath(name).stem
        for name in payloads
        if name.startswith("src/portfolio_endpoint/") and name.endswith(".py")
    }
    for name, data in payloads.items():
        if not name.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(data.decode("utf-8-sig"), filename=name)):
            imported = None
            if isinstance(node, ast.ImportFrom):
                if node.level == 1:
                    imported = node.module.split(".")[0] if node.module else None
                    if node.module is None:
                        for alias in node.names:
                            if alias.name not in available:
                                raise ValueError(f"{name}: omitted package dependency {alias.name}")
                elif node.module and node.module.startswith("portfolio_endpoint."):
                    imported = node.module.split(".")[1]
                elif node.module == "portfolio_endpoint":
                    for alias in node.names:
                        if alias.name not in available:
                            raise ValueError(f"{name}: omitted package dependency {alias.name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("portfolio_endpoint."):
                        imported = alias.name.split(".")[1]
                        if imported not in available:
                            raise ValueError(f"{name}: omitted package dependency {imported}")
            if imported and imported not in available:
                raise ValueError(f"{name}: omitted package dependency {imported}")


def release_project_text(text: str) -> str:
    """Keep package metadata but install only current scientific entry points."""
    import re

    block = (
        "[project.scripts]\n"
        + "".join(
            f'{name} = "portfolio_endpoint.{module}:main"\n' for name, module in SCRIPTS.items()
        )
        + "\n"
    )
    return re.sub(r"\[project\.scripts\]\n.*?(?=\n\[)", block, text, flags=re.S)


def build(root: Path, source_zip: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError("Choose a new archive filename; existing releases are preserved")
    verify_inputs(root)
    payloads = {
        f"src/portfolio_endpoint/{name}.py": (
            root / "src/portfolio_endpoint" / (name + ".py")
        ).read_bytes()
        for name in MODULES
    }
    for path in sorted((root / "tests").glob("test_*.py")):
        payloads[path.relative_to(root).as_posix()] = path.read_bytes()
    for path in sorted((root / "tests/fixtures").rglob("*")):
        if path.is_file():
            payloads[path.relative_to(root).as_posix()] = path.read_bytes()
    for path in sorted((root / "audits").rglob("*")):
        if path.is_file():
            payloads[path.relative_to(root).as_posix()] = path.read_bytes()
    for path in sorted((root / "generated").glob("*")):
        if path.is_file():
            payloads[path.relative_to(root).as_posix()] = path.read_bytes()
    inventory = json.loads((root / "replication/qf_input_manifest.json").read_text())
    for name in inventory["files"]:
        payloads[name] = manifest_target(root, name).read_bytes()
    for name in (
        "requirements-frozen.txt",
        ".gitattributes",
        "replication/RELEASE_NOTES.md",
        "SCIENTIFIC_CORE.md",
        "QF_V4_PUBLICATION.md",
        "config/experiment.yaml",
        "replication/qf_input_manifest.json",
        "replication/qf_reference_table_bodies.json",
        "replication/frozen_run_registry.json",
        "scripts/reproduce_qf.py",
        "scripts/reproduce_publication.py",
        "scripts/build_supplement_A6_A7.py",
        "scripts/validate_publication_results.py",
        ".python-version",
        "data/README.md",
        "CITATION.cff",
        "replication/QF_RELEASE_README.md",
        "replication/QF_RELEASE_STATUS.md",
    ):
        payloads[name] = (root / name).read_bytes()
    payloads["replication/qf_source_template.zip"] = source_zip.read_bytes()
    payloads["pyproject.toml"] = release_project_text(
        (root / "pyproject.toml").read_text()
    ).encode()
    payloads["README.md"] = (root / "replication/QF_RELEASE_README.md").read_bytes()
    payloads["RELEASE_STATUS.md"] = (root / "replication/QF_RELEASE_STATUS.md").read_bytes()
    if (root / "LICENSE").is_file():
        payloads["LICENSE"] = (root / "LICENSE").read_bytes()
    assert_dependency_closure(payloads)
    manifest = {
        "release": "v1.0.0-paper-submission",
        "scope": "Local frozen submission companion; not publicly deposited",
        "excluded_modules": list(EXCLUDED_MODULES),
        "files": {
            name: hashlib.sha256(data).hexdigest() for name, data in sorted(payloads.items())
        },
    }
    payloads["replication/RELEASE_MANIFEST.json"] = json.dumps(manifest, indent=2).encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payloads.items()):
            archive.writestr(name, data)
    print(
        json.dumps(
            {"archive": str(target), "files": len(payloads), "sha256": sha256(target)}, indent=2
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--source-zip", type=Path)
    parser.add_argument(
        "--output", type=Path, default=project_root() / "release/QF_V4_REPLICATION_CANDIDATE.zip"
    )
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify), indent=2))
    elif args.source_zip:
        build(project_root(), args.source_zip, args.output)
    else:
        parser.error("Supply --verify or --source-zip; no upload is performed")


if __name__ == "__main__":
    main()
