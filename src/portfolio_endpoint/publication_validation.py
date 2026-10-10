"""Verify generated tables against independent frozen references and committed sources."""

import argparse
import json
from pathlib import Path

from .ingest import project_root, sha256
from .provenance import verify_inputs, verify_manifest

def validate(root, output, *, check_inputs=True, ignore_provenance=False):
    if check_inputs:
        print(verify_inputs(root))
    else:
        print(verify_manifest(root, json.loads((output / "sources/regenerated_inputs.json").read_text())))
    reference = json.loads((root / "replication/qf_reference_table_bodies.json").read_text())
    actual = json.loads((output / "sources/publication_table_bodies.json").read_text())
    if actual != reference:
        raise ValueError("Core table bodies differ from the frozen reference")
    audit = json.loads((output / "EXPORT_MANIFEST.json").read_text())
    if audit["printed_numeric_discrepancies"]:
        raise ValueError("Printed values differ from the submitted source")
    references = json.loads((root / "replication/reference_outputs.json").read_text())
    from .design_sensitivity import summarize
    import pandas as pd
    headline = summarize(pd.read_csv(root / "results/primary_17_definitive_B2000/endpoint_pairs.csv", parse_dates=["earlier_endpoint", "later_endpoint"]))
    expected = references["design_headlines"]
    for name in ("n_pairs", "switch_count", "loss_gt25_count"):
        if headline[name] != expected[name]:
            raise ValueError("Baseline headline differs from frozen reference: " + name)
    for name, precision in (("switch_rate_pct", 1), ("loss_gt25_rate_pct", 1), ("mean_loss_ceq_bp", 2)):
        if format(headline[name], f".{precision}f") != expected[name]:
            raise ValueError("Baseline headline differs from frozen reference: " + name)
    expected_hashes = references["tables"]
    for name, digest in expected_hashes.items():
        target = root / "generated" / name if ignore_provenance else output / "tables" / name
        if sha256(target) != digest:
            raise ValueError("Table checksum differs from reference: " + name)
    for expected in sorted((root / "generated").glob("table_*.tex")):
        generated = output / "tables" / expected.name
        if ignore_provenance:
            content = lambda path: [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("%")]
            matches = content(generated) == content(expected)
        else:
            matches = generated.read_bytes() == expected.read_bytes()
        if not matches:
            raise ValueError("Generated table differs from committed source: " + expected.name)
    print("Validated nine tables against committed UTF-8 sources and frozen numerical audits.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    root = project_root(args.root)
    validate(root, args.output_dir or root / "results/reproduced_publication")

if __name__ == "__main__":
    main()
