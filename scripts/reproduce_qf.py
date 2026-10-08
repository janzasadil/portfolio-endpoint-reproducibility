"""One-command QF table/figure reproduction from the frozen companion package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from portfolio_endpoint.qf_publication import assemble
from portfolio_endpoint.qf_release import verify, verify_inputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-zip", type=Path, default=ROOT / "replication/qf_source_template.zip"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/reproduced_qf")
    args = parser.parse_args()
    if (ROOT / "replication/RELEASE_MANIFEST.json").exists():
        print(verify(ROOT))
    print(verify_inputs(ROOT))
    assemble(ROOT, args.source_zip, args.output_dir, regenerate_figures=True)
    expected = json.loads((ROOT / "replication/qf_reference_table_bodies.json").read_text())
    actual = json.loads((args.output_dir / "sources/publication_table_bodies.json").read_text())
    if actual != expected:
        raise ValueError("Generated tables differ from the frozen V4 reference")
    audit = json.loads((args.output_dir / "EXPORT_MANIFEST.json").read_text())
    if audit["printed_numeric_discrepancies"]:
        raise ValueError("Generated values differ from the submitted V4 source")
    print(
        "Verified: seven V4 tables match; four figures regenerated from frozen saved diagnostics."
    )


if __name__ == "__main__":
    main()
