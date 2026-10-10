# Reproduction

The analysis was validated with Python 3.13.3. Create and activate a virtual environment, then install the frozen environment as described in the [README](../README.md).

## Full reproduction

The full reproduction starts from the three raw datasets from the Kenneth R. French Data Library:

```bash
python scripts/reproduce_analysis.py
```

Missing raw archives are downloaded automatically. Alternatively, place the three ZIP files in one directory and run:

```bash
python scripts/reproduce_analysis.py --raw-dir PATH_TO_ZIPS
```

The script rebuilds the processed datasets and portfolio paths, reruns the paper's bootstrap and sensitivity analyses, and generates all publication tables and figures. It performs 6,000 bootstrap replications in total, so the full run is computationally substantial.

Results are written to `results/full_reproduction/`. Interrupted bootstrap runs can be continued with:

```bash
python scripts/reproduce_analysis.py --resume
```

Use `--plan` to inspect the run without computing and `--smoke` for a lightweight check of the full pipeline.

Sample periods, asset ordering, specifications, and random seeds match the paper. The industry data currently available from the French Data Library may include historical revisions relative to the version used for the submitted paper. The reproduction report records the input hashes and compares regenerated results with the submitted tables. Exact submitted values therefore require the original data vintage.

## Data provenance

The paper uses value-weighted monthly returns from the Kenneth R. French Data Library for:

- 17 U.S. industry portfolios;
- 30 U.S. industry portfolios;
- 14 developed-country markets.

Exact source files, checksums, sample coverage, and processed-data hashes are recorded in `replication/data_manifest.json`.

Source data remain subject to their original terms of use.

## Faster reproduction from saved results

If the original saved results are available, the publication outputs can be regenerated without rerunning portfolio construction or the bootstrap analysis:

```bash
python scripts/reproduce_publication.py --output-dir results/reproduced_publication
```

This generates Tables 1, 2, A1-A7 and Figures 1, 2, A1 and A2, together with the corresponding source files and validation reports.

The saved-results archive is optional and is not required for full reproduction from raw data.

## Journal source

A journal-source package can optionally be assembled with:

```bash
python scripts/assemble_manuscript.py --source-zip PATH_TO_JOURNAL_SOURCE.zip --output-dir results/journal_source
```

The journal template is not required to reproduce the analysis.

## Validation

Run the tests with:

```bash
python -m pytest -q
python -m pytest -q exploratory
```

Publication outputs generated from saved results can also be checked with:

```bash
python scripts/validate_publication_results.py --output-dir results/reproduced_publication
```

Tables are checked against the reference outputs and independent numerical checks. PDF binary identity across rendering-library versions is not required.

## Verification

The raw-data pipeline was verified with a smoke reproduction from the original three raw archives. The smoke run successfully regenerated the analysis, tables, and core figures, with numerical checks agreeing with the saved references.

The full 6,000-replication bootstrap was not rerun during the final verification.
