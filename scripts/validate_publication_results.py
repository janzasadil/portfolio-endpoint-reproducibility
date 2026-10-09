"""Validate frozen identities and byte-identical committed publication tables."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from portfolio_endpoint.qf_release import verify_inputs


def validate(output):
    print(verify_inputs(ROOT))
    reference = json.loads((ROOT / "replication/qf_reference_table_bodies.json").read_text())
    actual = json.loads((output / "sources/publication_table_bodies.json").read_text())
    if actual != reference:
        raise ValueError("Core table bodies differ from the frozen reference")
    audit = json.loads((output / "EXPORT_MANIFEST.json").read_text())
    if audit["printed_numeric_discrepancies"]:
        raise ValueError("Printed values differ from the submitted source")
    for expected in sorted((ROOT / "generated").glob("table_*.tex")):
        generated = output / "tables" / expected.name
        if generated.read_bytes() != expected.read_bytes():
            raise ValueError("Generated table differs from committed source: " + expected.name)
    print("Validated nine tables against committed UTF-8 sources and frozen numerical audits.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/reproduced_publication")
    validate(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
