"""Build a deterministic scientific replication archive without journal or raw assets."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import zipfile
from pathlib import PurePosixPath

from .ingest import project_root, sha256
from .provenance import manifest_target, verify, verify_inputs, verify_manifest

MODULES = tuple(sorted(p.stem for p in Path(__file__).parent.glob("*.py")))

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


def write_archive(payloads, target):
    if target.exists():
        raise FileExistsError("Choose a new archive filename; existing releases are preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(root, target):
    verify_inputs(root)
    payloads = {}
    for folder in ("src", "tests", "generated"):
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc" and not any(part.endswith(".egg-info") for part in path.parts):
                payloads[path.relative_to(root).as_posix()] = path.read_bytes()
    # Exploratory checks are maintained separately and are outside the scientific archive.
    for relative in (
        "README.md", "LICENSE", "CITATION.cff", "pyproject.toml", ".python-version",
        ".gitattributes", "requirements-frozen.txt", "config/paper_design.yaml",
        "docs/REPRODUCIBILITY.md",
        "replication/publication_inputs.json", "replication/full_empirical_archive.json",
        "replication/data_manifest.json", "replication/journal_template.json", "replication/frozen_run_registry.json",
        "replication/qf_reference_table_bodies.json", "replication/reference_outputs.json",
        "scripts/reproduce_publication.py", "scripts/reproduce_results.py",
        "scripts/reproduce_analysis.py",
        "scripts/assemble_manuscript.py", "scripts/validate_publication_results.py",
        "scripts/build_supplement_A6_A7.py",
    ):
        payloads[relative] = (root / relative).read_bytes()
    inventory = json.loads((root / "replication/publication_inputs.json").read_text())
    for name in inventory["files"]:
        payloads[name] = manifest_target(root, name).read_bytes()
    assert_dependency_closure(payloads)
    manifest = {"format_version": 1, "scope": "scientific publication reproduction",
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payloads.items())}}
    payloads["replication/RELEASE_MANIFEST.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    write_archive(payloads, target)
    print(json.dumps({"archive": str(target), "files": len(payloads), "sha256": sha256(target)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(project_root(args.root), args.output)


if __name__ == "__main__":
    main()
