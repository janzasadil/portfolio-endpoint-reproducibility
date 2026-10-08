"""Tracked evidence must preserve the original audit/provenance bytes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tracked_audit_snapshots_match_manifest():
    manifest = json.loads((ROOT / 'audits/SNAPSHOT_MANIFEST.json').read_text())
    for name, entry in manifest['audit_files'].items():
        snapshot = ROOT / 'audits' / name
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == entry['sha256'], name


def test_historical_run_registry_matches_preserved_snapshot():
    manifest = json.loads((ROOT / 'audits/SNAPSHOT_MANIFEST.json').read_text())
    registry = ROOT / 'replication/frozen_run_registry.json'
    expected = manifest['historical_run_registry']['sha256']
    assert hashlib.sha256(registry.read_bytes()).hexdigest() == expected
