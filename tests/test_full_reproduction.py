import json
from pathlib import Path

import pandas as pd
import pytest

from portfolio_endpoint import full_reproduction as full
from portfolio_endpoint import ingest

ROOT = Path(__file__).resolve().parents[1]


def test_raw_analysis_plan_matches_executed_registry():
    plan = full.analysis_plan(ROOT)
    assert len(plan) == 8
    assert sum(run["replications"] for run in plan) == 6000
    assert {run["seed"] for run in plan} == {20260909}
    assert [run["fixed_block_length"] for run in plan if run["fixed_block_length"]] == [12, 24]
    assert [run["lookback"] for run in plan[-3:]] == [36, 120, 60]
    assert plan[-1]["rebalance_every"] == 3
    assert plan[0]["enhanced"]


def test_raw_ingestion_fixes_calendar_assets_and_country_date_header(tmp_path, monkeypatch):
    from portfolio_endpoint import countries
    raw = tmp_path / "data/raw/country.zip"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"local raw fixture")
    index = pd.date_range("2000-01-31", periods=4, freq="ME")
    panel = pd.DataFrame({"B": [0.1] * 4, "A": [0.2] * 4, "extra": [0.3] * 4}, index=index)
    monkeypatch.setattr(countries, "parse_broader_country_markets", lambda archive: (panel, {}))
    spec = {"parser": "international_countries", "raw_file": "country.zip", "processed_file": "country.csv",
            "sample_start": "2000-01-31", "sample_end": "2000-03-31", "columns": ["A", "B"]}
    ingest.ingest_dataset("country", spec, tmp_path)
    parsed = pd.read_csv(tmp_path / "data/processed/country.csv", index_col="date")
    assert b"\r\n" in (tmp_path / "data/processed/country.csv").read_bytes()
    assert len(parsed) == 3
    assert list(parsed) == ["A", "B"]
    assert parsed.iloc[0].tolist() == [0.2, 0.1]
    spec["sample_end"] = "2000-05-31"
    with pytest.raises(ValueError, match="cover"):
        ingest.ingest_dataset("country", spec, tmp_path)


def test_raw_download_never_marks_partial_payload_as_valid_archive(tmp_path, monkeypatch):
    def broken(url, target):
        Path(target).write_bytes(b"partial payload")
        raise OSError("interrupted download")
    monkeypatch.setattr(ingest, "urlretrieve", broken)
    spec = {"raw_file": "data.zip", "processed_file": "data.csv", "url": "https://example.test/data.zip"}
    with pytest.raises(OSError, match="interrupted"):
        ingest.ingest_dataset("dataset", spec, tmp_path)
    assert not (tmp_path / "data/raw/data.zip").exists()


def test_full_analysis_does_not_copy_saved_results(tmp_path, monkeypatch):
    import yaml
    from portfolio_endpoint import study
    def fake_ingest(name, spec, work):
        raw = work / "data/raw" / spec["raw_file"]
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"raw")
        target = work / "data/processed" / spec["processed_file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({c: 0.01 for c in spec["columns"]},
                     index=pd.date_range(spec["sample_start"], spec["sample_end"], freq="ME", name="date")).to_csv(target)
    class ReachedComputation(Exception):
        pass
    work = tmp_path / "raw_only"
    def check_study(arguments):
        assert not (work / "results").exists()
        assert arguments[arguments.index("--outer-reps") + 1] == "2000"
        assert len(list((work / "data/processed").glob("*.csv"))) == 3
        raise ReachedComputation()
    monkeypatch.setattr(full, "ingest_dataset", fake_ingest)
    monkeypatch.setattr(study, "main", check_study)
    with pytest.raises(ReachedComputation):
        full.full_reproduction(ROOT, work)
    state = json.loads((work / "ANALYSIS_STATE.json").read_text())
    assert not state["completed"]
    assert set(state["identity"]["raw"]) == {s["raw_file"] for s in yaml.safe_load((ROOT / "config/paper_design.yaml").read_text())["datasets"].values()}
    partial = work / "results" / full.analysis_plan(ROOT)[0]["name"]
    partial.mkdir(parents=True)
    (partial / "unfinished.txt").write_text("preserve this partial stage")
    def check_restart(arguments):
        assert not partial.exists()
        archived = work / "incomplete" / partial.name / "unfinished.txt"
        assert archived.read_text() == "preserve this partial stage"
        assert "--resume" not in arguments
        raise ReachedComputation()
    monkeypatch.setattr(study, "main", check_restart)
    with pytest.raises(ReachedComputation):
        full.full_reproduction(ROOT, work, resume=True)
    # Changing any input refuses a resume before computation.
    first = next((work / "data/raw").glob("*.zip"))
    first.write_bytes(b"changed")
    with pytest.raises(ValueError, match="identity changed"):
        full.full_reproduction(ROOT, work, resume=True)


def test_registered_bootstrap_resume_adds_only_missing_draws(tmp_path):
    run = full.analysis_plan(ROOT)[0]
    folder = tmp_path / "results" / run["name"]
    folder.mkdir(parents=True)
    pd.DataFrame({"replication": range(1990)}).to_csv(folder / "outer_bootstrap.csv", index=False)
    arguments = full.study_arguments(tmp_path, run)
    assert "--resume" in arguments
    assert arguments[arguments.index("--outer-reps") + 1] == "10"
    pd.DataFrame({"replication": range(2000)}).to_csv(folder / "outer_bootstrap.csv", index=False)
    assert "--finalize" in full.study_arguments(tmp_path, run)


def test_checkpoint_finalization_preserves_draws_without_resampling(tmp_path, monkeypatch):
    import yaml
    from portfolio_endpoint import study
    (tmp_path / "config").mkdir()
    (tmp_path / "pyproject.toml").write_text("")
    configuration = yaml.safe_load((ROOT / "config/paper_design.yaml").read_text())
    (tmp_path / "config/paper_design.yaml").write_text(yaml.safe_dump(configuration))
    source = tmp_path / "data/processed" / configuration["datasets"]["primary_17_industry"]["processed_file"]
    source.parent.mkdir(parents=True)
    pd.DataFrame({"asset": [0.01] * 12}, index=pd.date_range("2000-01-31", periods=12, freq="ME", name="date")).to_csv(source)
    monkeypatch.setattr(study, "protocol_block_length", lambda returns: 3)
    monkeypatch.setattr(study, "run_headline_paths", lambda *args: {})
    frame = pd.DataFrame({"value": [1]})
    monkeypatch.setattr(study, "endpoint_reproducibility", lambda *args: frame)
    monkeypatch.setattr(study, "endpoint_summary", lambda frame: {"mean_endpoint_loss": 0.01, "n_origins": 1})
    monkeypatch.setattr(study, "winner_survival", lambda *args: frame)
    monkeypatch.setattr(study, "kaplan_meier", lambda frame: frame)
    monkeypatch.setattr(study, "survival_summary", lambda frame: {"median_survival_months": 12})
    monkeypatch.setattr(study, "ceq_accounting", lambda *args: frame)
    selections = pd.DataFrame({name: [0.1] for name in ("selection_regret", "selector_minus_ensemble", "selector_hit", "selector_rank")})
    monkeypatch.setattr(study, "ex_ante_selection", lambda *args: selections)
    columns = ("mean_endpoint_loss", "literal_switch_frequency", "survival_12_months", "survival_24_months",
               "mean_selection_regret", "mean_selector_minus_ensemble", "selector_hit_rate", "mean_selector_rank")
    draws = pd.DataFrame({**{name: [0.1] for name in columns}, "replication": [0], "block_length": [3]})
    monkeypatch.setattr(study, "outer_bootstrap", lambda **kwargs: draws)
    arguments = ["--root", str(tmp_path), "--run-name", "checkpoint"]
    study.main([*arguments, "--outer-reps", "1"])
    def forbidden(**kwargs):
        pytest.fail("Finalizing an existing checkpoint must not resample")
    monkeypatch.setattr(study, "outer_bootstrap", forbidden)
    study.main([*arguments, "--resume", "--finalize"])
    output = tmp_path / "results/checkpoint"
    pd.testing.assert_frame_equal(pd.read_csv(output / "outer_bootstrap.csv"), draws)
    assert json.loads((output / "summary.json").read_text())["outer_bootstrap_replications"] == 1


def test_revised_data_export_keeps_consistency_checks_without_forcing_paper_headlines():
    from portfolio_endpoint.fixed_method_benchmark import validate_headlines
    summary = {"n_decisions": 80, "preceding_winner_hit_rate": 0.4, "preceding_winner_mean_regret_bp": 100.0}
    saved = {"selector_hit_rate": 0.4, "mean_selection_regret": 0.01}
    original = ("run", 75, "38.7", "109.12")
    validate_headlines(summary, saved, original, check_reference=False)
    with pytest.raises(ValueError, match="count mismatch"):
        validate_headlines(summary, saved, original)
    with pytest.raises(ValueError, match="differ"):
        validate_headlines(summary, {**saved, "selector_hit_rate": 0.5}, original, check_reference=False)


def test_partial_bootstrap_checkpoint_is_rejected_before_resume():
    from portfolio_endpoint.study import validate_resume
    identity = {"block_length": 12, "enhanced_sensitivities": False}
    draws = pd.DataFrame({"replication": [0], "block_length": [12], "mean_endpoint_loss": [float("nan")]})
    with pytest.raises(ValueError, match="incomplete"):
        validate_resume(draws, {"run_identity": identity}, identity)
    censored = draws.assign(mean_endpoint_loss=0.001, median_survival_months=float("nan"))
    assert validate_resume(censored, {"run_identity": identity}, identity) == 1
