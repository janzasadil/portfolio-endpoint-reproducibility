import sys

import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint import study
from portfolio_endpoint.bootstrap import corrected_pw_stationary_block_length
from portfolio_endpoint.countries import _market_from_text
from portfolio_endpoint.engine import run_continuous_path
from portfolio_endpoint.qf_tables import format_percentage, replace_table_bodies
from portfolio_endpoint.ingest import ingest_dataset, parse_value_weighted_monthly


def test_pw_no_insignificant_run_uses_maximum_bandwidth():
    # A persistent trend has no qualifying run in the ACF search. The bounded
    # maximum-bandwidth reference result is 14; the buggy fallback returned 5.
    assert corrected_pw_stationary_block_length(np.arange(200, dtype=float)) == 14


def test_industry_parser_rejects_missing_calendar_month():
    text = 'Average Value Weighted Returns -- Monthly\n,Food\n200001,1\n200003,2\n'
    with pytest.raises(ValueError, match="uninterrupted"):
        parse_value_weighted_monthly(text)


def test_country_parser_rejects_duplicate_before_aggregation():
    text = 'Value-Weight Dollar Returns      All 4 Data Items Not Reqd\n197501 1\n197501 2\n'
    with pytest.raises(ValueError, match="dates"):
        _market_from_text(text)


def test_engine_rejects_gaps_before_evaluating_rule():
    frame = pd.DataFrame({"a": [0, 0, 0]}, index=pd.to_datetime(['2000-01-31', '2000-03-31', '2000-04-30']))
    def forbidden(history):
        raise AssertionError("Must validate dates before estimating weights")
    with pytest.raises(ValueError, match="uninterrupted"):
        run_continuous_path(frame, forbidden, 2, .0025)


@pytest.mark.parametrize("options", [
    ['--outer-reps', '1', '--rebalance-every', '3'],
    ['--enhanced-sensitivities', '--fixed-block-length', '12'],
    ['--resume'],
])
def test_unsupported_cli_combinations_fail_before_reading_or_writing(monkeypatch, options):
    monkeypatch.setattr(sys, 'argv', ['portfolio-study', *options])
    monkeypatch.setattr(study, 'project_root', lambda: pytest.fail('Must fail before touching filesystem'))
    with pytest.raises(SystemExit):
        study.main()


def test_resume_checks_identity_and_registry():
    identity = {'block_length': 12, 'enhanced_sensitivities': False, 'seed': 99}
    draws = pd.DataFrame({'replication': [0, 1], 'block_length': [12, 12], 'mean_endpoint_loss': [0, .1]})
    assert study.validate_resume(draws, {'run_identity': identity}, identity) == 2
    with pytest.raises(ValueError, match="identity"):
        study.validate_resume(draws, {}, identity)
    with pytest.raises(ValueError, match="identity"):
        study.validate_resume(draws, {'run_identity': {**identity, 'seed': 98}}, identity)
    with pytest.raises(ValueError, match="contiguous"):
        study.validate_resume(draws.assign(replication=[0, 2]), {'run_identity': identity}, identity)
    with pytest.raises(ValueError, match="block"):
        study.validate_resume(draws.assign(block_length=[12, 24]), {'run_identity': identity}, identity)


def test_display_rounds_once_from_native_proportions():
    assert format_percentage(10 / 83) == r'12.0\%'
    assert format_percentage(11 / 83) == r'13.3\%'


def test_layout_templates_cannot_silently_keep_old_numeric_bodies():
    template = r'\midrule old rows\bottomrule \midrule stale rows\bottomrule'
    replaced = replace_table_bodies(template, ['new one', 'new two'])
    assert 'old rows' not in replaced and 'stale rows' not in replaced
    with pytest.raises(ValueError, match='Layout mismatch'):
        replace_table_bodies(template, ['only one'])


def test_default_ingestion_dispatches_country_dat_archive(monkeypatch, tmp_path):
    import zipfile
    archive = tmp_path / 'data/raw/F-F_International_Countries.zip'
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('Austrlia.Dat', 'Value-Weight Dollar Returns      All 4 Data Items Not Reqd\n197501 1\n197502 2\n')
    ingest_dataset('countries', {'raw_file': archive.name, 'processed_file': 'countries.csv', 'parser': 'international_countries'}, tmp_path)
    panel = pd.read_csv(tmp_path / 'data/processed/countries.csv')
    assert panel.Australia.tolist() == [.01, .02]
    assert (tmp_path / 'results/country_extension/country_data_audit.json').exists()


def test_release_integrity_rejects_modified_frozen_input(tmp_path):
    import hashlib
    import json
    from portfolio_endpoint.qf_release import verify
    (tmp_path / 'replication').mkdir()
    target = tmp_path / 'frozen.csv'
    target.write_bytes(b'original')
    manifest = {'release': 'test', 'files': {'frozen.csv': hashlib.sha256(b'original').hexdigest()}}
    (tmp_path / 'replication/RELEASE_MANIFEST.json').write_text(json.dumps(manifest))
    assert verify(tmp_path)['verified_files'] == 1
    target.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        verify(tmp_path)
