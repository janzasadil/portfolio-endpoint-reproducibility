"""Path-safe verification of saved inputs and deterministic provenance."""

import json
from pathlib import Path, PurePosixPath

from .ingest import sha256


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
        raise ValueError(f"Saved input files missing or changed: {failures}")
    return {"verified_files": len(manifest["files"]),
            "release": manifest.get("release", "publication inputs")}


def verify(root: Path) -> dict:
    return verify_manifest(root, json.loads((root / "replication/RELEASE_MANIFEST.json").read_text()))


def verify_inputs(root: Path) -> dict:
    return verify_manifest(root, json.loads((root / "replication/publication_inputs.json").read_text()))


def verify_template(root: Path, template: Path) -> None:
    expected = json.loads((root / "replication/journal_template.json").read_text())["sha256"]
    if sha256(template) != expected:
        raise ValueError("Journal template differs from the pinned paper source")
