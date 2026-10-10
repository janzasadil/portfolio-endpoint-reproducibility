import ast
from pathlib import Path

import pytest
import tomllib

from portfolio_endpoint import qf_tables
from portfolio_endpoint.qf_release import (
    MODULES,
    assert_dependency_closure,
    manifest_target,
    verify_manifest,
)


def test_qf_pipeline_and_tests_have_no_legacy_package_imports():
    root = Path(__file__).resolve().parents[1]
    payloads = {
        f"src/portfolio_endpoint/{m}.py": (
            root / "src/portfolio_endpoint" / (m + ".py")
        ).read_bytes()
        for m in MODULES
    }
    payloads.update(
        {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "tests").glob("test_*.py")}
    )
    assert_dependency_closure(payloads)
    assert not {"near_tie", "frl_publication", "reporting"} & set(MODULES)


def test_qf_table_builder_does_not_require_old_near_tie_input():
    source = Path(qf_tables.__file__).read_text()
    assert "near_tie" not in source
    assert "frl_publication" not in source
    assert "final_publication" not in source
    ast.parse(source)


def test_release_metadata_omits_legacy_entry_points():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    commands = project["project"]["scripts"]
    assert "portfolio-qf-publication" in commands
    assert not {
        "portfolio-report",
        "portfolio-frl-publication",
        "portfolio-near-tie",
        "portfolio-post-referee",
        "portfolio-country-bootstrap-report",
    } & set(commands)


def test_archive_dependency_closure_fails_for_local_or_absolute_legacy_import():
    for code in (
        "from .near_tie import main",
        "from . import reporting",
        "from portfolio_endpoint.final_publication import final_tables",
        "from portfolio_endpoint import reporting",
        "import portfolio_endpoint.post_referee",
    ):
        with pytest.raises(ValueError, match="omitted package dependency"):
            assert_dependency_closure({"src/portfolio_endpoint/qf.py": code.encode()})


@pytest.mark.parametrize(
    "name", ["../outside.csv", "/outside.csv", "C:/outside.csv", "a\\..\\outside.csv"]
)
def test_archive_manifest_rejects_escaping_paths(tmp_path, name):
    with pytest.raises(ValueError, match="escapes"):
        manifest_target(tmp_path, name)


def test_frozen_input_verifier_fails_when_required_file_missing(tmp_path):
    with pytest.raises(ValueError, match="missing or changed"):
        verify_manifest(tmp_path, {"files": {"missing.csv": "0" * 64}})
