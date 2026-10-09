"""Reproduce all paper tables and four core figures from frozen saved results."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from portfolio_endpoint.qf_publication import assemble
from portfolio_endpoint.qf_release import verify, verify_inputs
from portfolio_endpoint.supplement_inputs import read_frozen
from portfolio_endpoint.change_return import change_and_return
from portfolio_endpoint.ceq_component_decomposition import reversal_points, return_risk
from build_supplement_A6_A7 import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, default=ROOT / "replication/qf_source_template.zip")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/reproduced_publication")
    parser.add_argument("--gap-scatter", action="store_true", help="Also render the optional gap/perturbation diagnostic; not inserted into the paper")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("Choose a fresh output directory")
    if (ROOT / "replication/RELEASE_MANIFEST.json").exists():
        print(verify(ROOT))
    print(verify_inputs(ROOT))
    inputs = read_frozen(ROOT)
    change_and_return(ROOT, inputs)
    points = reversal_points(inputs)
    return_risk(ROOT, inputs, points)
    assemble(ROOT, args.source_zip, args.output_dir, regenerate_figures=True)
    build(ROOT, args.output_dir)
    from validate_publication_results import validate
    validate(args.output_dir)
    if args.gap_scatter:
        from portfolio_endpoint.plot_gap_perturbation import gap_figure
        gap_figure(ROOT, points)
    print("Reproduced Tables 1, 2, A1-A7 and four core figures; native A6/A7 inputs included.")


if __name__ == "__main__":
    main()
