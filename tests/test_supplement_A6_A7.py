"""Verify reproducibility and source validation for the supplemental exporter."""
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/supplement"
from portfolio_endpoint import supplement_tables as exporter


def test_supplement_build_is_deterministic_and_includes_native_tables(tmp_path):
    output = tmp_path / "publication"
    output.mkdir()
    manuscript = output / "supplemental_material.tex"
    manuscript.write_text("\\input{tables/table_A5.tex}\n\\end{document}\n")
    exporter.build(FIXTURES, output)
    first = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    exporter.build(FIXTURES, output)
    second = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert first == second
    for name in ("table_A6", "table_A7"):
        assert manuscript.read_text() == "\\input{tables/table_A5.tex}\n\\end{document}\n"
        generated = (output / "tables" / (name + ".tex")).read_text()
        assert generated.startswith("% AUTO-GENERATED FILE. DO NOT EDIT BY HAND.\n")
        approved = (ROOT / "generated" / (name + ".tex")).read_text()
        assert generated == approved
        assert (output / "tables" / (name + ".tex")).read_bytes() == (ROOT / "generated" / (name + ".tex")).read_bytes()


def test_supplement_rejects_summary_inconsistent_with_origins(tmp_path):
    for relative in (
        "results/change_and_return/summary.csv",
        "results/change_and_return/origins.csv",
        "results/return_risk_decomposition/summary.csv",
        "results/return_risk_decomposition/observations.csv",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / relative, target)
    summary = tmp_path / "results/change_and_return/summary.csv"
    frame = exporter.pd.read_csv(summary)
    frame.loc[0, "n_eligible"] += 1
    frame.to_csv(summary, index=False)
    with pytest.raises(ValueError, match="eligible counts"):
        exporter.build(tmp_path, tmp_path / "publication")
