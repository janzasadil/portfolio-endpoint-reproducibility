from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import pytest

from portfolio_endpoint.analysis import TIE_BREAK_ORDER
from portfolio_endpoint.qf_publication import (
    assemble,
    compare_table_numbers,
    conditional_gap_statistics,
    interval_text,
    printed_numbers,
    template_prefix,
)


def test_numeric_audit_ignores_layout_dimensions_not_data():
    body = r"\multicolumn{3}{l}{Panel A}\\[-0.15em] \addlinespace[0.25em]"
    body += r"Value & 7.35 & \makecell{$-10.93$\\\footnotesize$(-75.42,\,186.92)$} \\"
    assert printed_numbers(body) == ["7.35", "-10.93", "-75.42", "186.92"]


def test_numeric_audit_detects_changed_value_missing_value_and_sign():
    template = r"\midrule A & 7.35 & -10.93 \\ \bottomrule"
    unchanged = compare_table_numbers("table", template, [r"A & 7.35 & -10.93 \\"])
    assert all(row["matches"] for row in unchanged)
    altered = compare_table_numbers("table", template, [r"A & 7.36 & +10.93 \\"])
    assert not any(row["matches"] for row in altered)
    missing = compare_table_numbers("table", template, [r"A & 7.35 \\"])
    assert missing[-1]["generated_numeric"] is None
    assert not missing[-1]["matches"]


def test_numeric_audit_rejects_wrong_panel_count():
    with pytest.raises(ValueError, match="layout"):
        compare_table_numbers("table", r"\midrule 1\bottomrule", ["1", "2"])


def test_conditional_gap_rows_use_shifted_winner_only_on_switches():
    score_pairs = [
        ([0.10, 0.09, 0, 0, 0], [0.05, 0.08, 0, 0, 0]),
        ([0.10, 0.09, 0, 0, 0], [0.10, 0.09, 0, 0, 0]),
        ([0.15, 0, 0.10, 0, 0], [0.11, 0, 0.12, 0, 0]),
    ]
    rows = []
    for earlier, later in score_pairs:
        initial, shifted = int(np.argmax(earlier)), int(np.argmax(later))
        rows.append(
            {
                "earlier_winner": TIE_BREAK_ORDER[initial],
                "later_winner": TIE_BREAK_ORDER[shifted],
                "literal_switch": initial != shifted,
                "endpoint_loss": later[shifted] - later[initial],
                **{f"earlier_ceq_{m}": earlier[i] for i, m in enumerate(TIE_BREAK_ORDER)},
                **{f"later_ceq_{m}": later[i] for i, m in enumerate(TIE_BREAK_ORDER)},
            }
        )
    pairs = pd.DataFrame(rows)
    result = conditional_gap_statistics(pairs)
    assert result["n"] == 2
    assert result["median_gap"] == pytest.approx(0.03)
    assert result["median_perturbation"] == pytest.approx(0.05)
    assert result["median_loss"] == pytest.approx(0.02)
    with pytest.raises(ValueError, match="decomposition"):
        conditional_gap_statistics(pairs.assign(endpoint_loss=99))


def test_interval_display_keeps_signed_mean_and_percentile_endpoints():
    text = interval_text(-0.001093007793422686, [-0.007542, 0.018692], signed=True)
    assert text == r"$-10.93$ $(-75.42,\,186.92)$"
    assert "makecell" in interval_text(0.000735, [0.000404, 0.001960], stacked=True)


def test_zip_prefix_supports_nested_and_flat_source_and_rejects_ambiguity(tmp_path):
    archive_path = tmp_path / "source.zip"
    for name, expected in [("main.tex", ""), ("package/main.tex", "package/")]:
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(name, "")
        with zipfile.ZipFile(archive_path) as archive:
            assert template_prefix(archive) == expected
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("one/main.tex", "")
        archive.writestr("two/main.tex", "")
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="exactly one"):
            template_prefix(archive)


def test_export_never_overwrites_an_existing_publication_directory(tmp_path):
    with pytest.raises(FileExistsError, match="fresh"):
        assemble(tmp_path, Path("missing.zip"), tmp_path)
