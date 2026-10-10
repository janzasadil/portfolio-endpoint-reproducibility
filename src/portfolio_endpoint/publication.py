"""Reproduce scientific outputs; optionally assemble a separately pinned journal source."""

import argparse
from pathlib import Path

from .ingest import project_root
from .provenance import verify_inputs, verify_template
from .qf_publication import assemble
from .publication_validation import validate


def reproduce(root, output, *, gap_scatter=False, source_zip=None):
    root, output = Path(root), Path(output)
    if output.exists():
        raise FileExistsError("Choose a fresh output directory")
    print(verify_inputs(root))
    if source_zip is not None:
        verify_template(root, source_zip)
    assemble(root, source_zip, output, regenerate_figures=True)
    validate(root, output)
    if gap_scatter:
        from .supplement_inputs import read_frozen
        from .ceq_component_decomposition import reversal_points
        from .plot_gap_perturbation import gap_figure
        points = reversal_points(read_frozen(root))
        gap_figure(root, points, output=output / "sources/gap_perturbation_scatter",
                   pdf=output / "figures/gap_perturbation_scatter.pdf")
    print("Reproduced Tables 1, 2, A1-A7 and four core figures.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--gap-scatter", action="store_true")
    args = parser.parse_args()
    root = project_root(args.root)
    reproduce(root, args.output_dir or root / "results/reproduced_publication", gap_scatter=args.gap_scatter)


def manuscript_main():
    parser = argparse.ArgumentParser(description="Optional journal-source assembly from pinned assets")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    reproduce(project_root(args.root), args.output_dir, source_zip=args.source_zip)


if __name__ == "__main__":
    main()
