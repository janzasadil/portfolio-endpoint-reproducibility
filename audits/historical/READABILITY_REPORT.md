# Readability-only pass

Scope: `extension.py`, `frl_publication.py`, `final_publication.py`, and the
test imports affected by helper renaming. No scientific specifications,
calculation rules, CSV schemas, filenames, or command-line options changed.

## Changes

- Replaced opaque helper names with descriptive names, including
  `_compute_baseline_statistics`, `_summarize_by_initial_winner`,
  `_leave_one_out`, and `replace_table_bodies`.
- Distinguished numeric unit conversions (`to_basis_points`, `to_percent`)
  from display formatting (`format_basis_points`, `format_percentage`).
- Renamed ambiguous locals for settings, endpoint pairs, summaries, saved
  intervals, portfolio paths, and legend handles/labels.
- Expanded semicolon-packed statements and long expressions into ordinary
  formatted Python. Added short explanatory docstrings; retained all existing
  comments, including scientific conventions.

## Verification

- All 35 tests passed (only existing Matplotlib/Pyparsing deprecation warnings).
- Compared all three modules against the pre-pass source snapshot in
  `tmp/reproducibility_cleanroom_v2/src/portfolio_endpoint`: their syntax trees
  match after accounting for renames, formatting, and docstrings. Original
  comments are preserved.
- Ten exact DataFrame comparisons passed for winner-conditioned statistics,
  transitions, and margin diagnostics using existing industry/country results.
- All eight final publication table bodies and their provenance match exactly.
- All 28 working export files match byte-for-byte, including four PNG figures.
  PDF writing was skipped during this check; no published PDFs were replaced.

Verification exports are isolated under `tmp/readability_verification`.
Existing publication directories, frozen results, and release archives were
not modified. No empirical analysis, robustness run, or bootstrap was rerun.
