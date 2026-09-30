import io
import zipfile

import pandas as pd

from portfolio_endpoint.countries import parse_broader_country_markets


def _country_text(rows):
    return "\n".join(["header", "     Value-Weight Dollar Returns      All 4 Data Items Not Reqd", "labels", *rows, "", "next section"])


def test_country_parser_selects_only_broader_mkt_and_freezes_complete_series(tmp_path):
    archive = tmp_path / "countries.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("Austrlia.Dat", _country_text(["197501 1.00 9", "197502 2.00 9"]))
        zipped.writestr("Belgium.Dat", _country_text(["197501 3.00 9", "197502 4.00 9"]))
    panel, audit = parse_broader_country_markets(archive)
    assert panel.columns.tolist() == ["Australia", "Belgium"]
    assert panel.iloc[0, 0] == 0.01
    assert audit["return_currency"] == "USD"
    assert audit["n_countries"] == 2


def test_country_parser_excludes_series_not_starting_in_january_1975(tmp_path):
    archive = tmp_path / "countries.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("Austrlia.Dat", _country_text(["197501 1.00 9", "197502 2.00 9"]))
        zipped.writestr("Belgium.Dat", _country_text(["197502 4.00 9"]))
    panel, audit = parse_broader_country_markets(archive)
    assert panel.columns.tolist() == ["Australia"]
    assert not audit["all_source_files"]["Belgium"]["uninterrupted_from_1975_01"]
