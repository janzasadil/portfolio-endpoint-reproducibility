"""Production cleanup guards: invariants, provenance and portable archive identity."""
import json
from pathlib import Path
import subprocess
import sys
import os
import zipfile

import pandas as pd
import pytest

from portfolio_endpoint import ingest
from portfolio_endpoint.qf_release import write_archive
from portfolio_endpoint.provenance import verify_template

ROOT = Path(__file__).resolve().parents[1]


def test_zip_identity_has_fixed_metadata_and_stable_bytes(tmp_path):
    first, second = tmp_path / "a.zip", tmp_path / "b.zip"
    write_archive({"b.txt": b"two", "a.txt": b"one"}, first)
    write_archive({"a.txt": b"one", "b.txt": b"two"}, second)
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == ["a.txt", "b.txt"]
        for member in archive.infolist():
            assert member.date_time == (1980, 1, 1, 0, 0, 0)
            assert member.external_attr >> 16 == 0o100644


def test_ingestion_provenance_is_idempotent_and_does_not_append_tracked_markdown(tmp_path):
    raw, processed = tmp_path / "raw.zip", tmp_path / "panel.csv"
    raw.write_bytes(b"source")
    panel = pd.DataFrame({"asset": [.01, .02]}, index=pd.date_range("2000-01-31", periods=2, freq="ME"))
    panel.to_csv(processed)
    artifact = tmp_path / "data/provenance/panel.json"
    ingest.write_data_provenance(artifact, "panel", raw, processed, panel)
    before = artifact.read_bytes()
    ingest.write_data_provenance(artifact, "panel", raw, processed, panel)
    assert artifact.read_bytes() == before
    assert "timestamp" not in json.loads(before)
    assert not (tmp_path / "DATA_MANIFEST.md").exists()


def test_wheel_path_cannot_guess_unrelated_repository_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ingest, "__file__", str(tmp_path / "site-packages/portfolio_endpoint/ingest.py"))
    with pytest.raises(ValueError, match="checkout"):
        ingest.project_root()
    checkout = tmp_path / "checkout"
    (checkout / "config").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("")
    (checkout / "config/paper_design.yaml").write_text("")
    assert ingest.project_root(checkout) == checkout.resolve()


def test_baseline_validation_survives_optimized_python(tmp_path):
    saved = tmp_path / "pairs.csv"
    saved.write_text("earlier_endpoint,later_endpoint\n2000-12-31,2001-12-31\n")
    code = "import pandas as pd; from pathlib import Path; from portfolio_endpoint.design_sensitivity import baseline_check; baseline_check(pd.DataFrame({'earlier_endpoint':pd.to_datetime([])}),Path(" + repr(str(saved)) + "),'17_industries')"
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    result = subprocess.run([sys.executable, "-O", "-c", code], env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert "ValueError" in result.stderr


def test_optional_journal_template_is_verified_before_use(tmp_path):
    (tmp_path / "replication").mkdir()
    template = tmp_path / "journal.zip"
    template.write_bytes(b"wrong")
    (tmp_path / "replication/journal_template.json").write_text(json.dumps({"sha256":"0" * 64}))
    with pytest.raises(ValueError, match="pinned"):
        verify_template(tmp_path, template)


def test_publication_manifest_excludes_raw_archives_but_full_provenance_keeps_them():
    publication = json.loads((ROOT / "replication/publication_inputs.json").read_text())
    full = json.loads((ROOT / "replication/full_empirical_archive.json").read_text())
    assert not any(name.startswith("data/raw/") for name in publication["files"])
    assert sum(name.startswith("data/raw/") for name in full["files"]) == 3


def test_executed_registry_retains_original_frozen_bytes():
    import hashlib
    reference = json.loads((ROOT / "replication/reference_outputs.json").read_text())
    assert hashlib.sha256((ROOT / "replication/frozen_run_registry.json").read_bytes()).hexdigest() == reference["executed_run_registry_sha256"]
