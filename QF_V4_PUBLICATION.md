# QF V4 table generation

Generate Tables 1, 2 and A1-A5 from existing frozen outputs. No portfolio
construction, endpoint analysis, robustness run or bootstrap is performed.
The submitted V4 ZIP supplies formatting, prose and bibliography, not numerical
table bodies. A preservation mode copies static figures for comparison; the
archival reproduction command regenerates all four figures from saved diagnostics.

From the repository root:

```powershell
python scripts/reproduce_qf.py
```

This is the preferred command after restoring the QF frozen companion archive.
It validates archive/input identities and writes to a fresh `results/reproduced_qf/`.
For a developer-supplied source ZIP or another fresh output directory:

```powershell
$env:PYTHONPATH = 'src'
python -m portfolio_endpoint.qf_publication --source-zip 'PATH_TO_V4_SOURCE.zip' --output-dir 'results/publication_qf_new' --regenerate-figures
```

After installing the project, `portfolio-qf-publication` is an equivalent command.
Choose a fresh output directory: the exporter refuses to overwrite an existing
package. It fails if required frozen outputs, expected prospective headlines,
settings, survival medians or saved bootstrap registries do not validate.

## Data sources

| Table | Saved inputs |
|---|---|
| 1 | Primary/country endpoint pairs and existing bootstrap draws; conditional gap decomposition uses the saved earlier/later method CEQs. |
| 2 | Primary/country prospective-selection CSVs, summaries and existing bootstrap draws; fixed-method benchmarks use saved future CEQs. |
| A1 | Existing specification summaries and material-survival diagnostic outputs. |
| A2 | Existing common-origin displacement, 30-industry, calendar-phase and H=60 robustness outputs. |
| A3 | Existing initial-winner-conditioned diagnostic outputs. |
| A4 | Existing stationary and circular-block draws and saved point estimates. |
| A5 | Validated portfolio settings and existing processed-data/sample information. |

The numerical exporter uses the standalone `qf_tables` builders where
the scientific objects are unchanged. It independently constructs the added V4
rows. `EXPORT_MANIFEST.json` records the inputs and submitted template checksum.
`sources/publication_table_bodies.json` contains generated LaTeX bodies.

`table_numeric_audit.csv` compares each printed numerical token with the supplied
source, including signs, counts and interval bounds, excluding layout dimensions.
Differences are reported, not resolved by substituting manuscript numbers.
`PAPER_CODE_AUDIT.md` and its JSON companion document implementation consistency
and recommended wording clarifications. This is not an external-literature audit.

## Compilation and scope

Compile `main.tex` and `supplemental_material.tex` separately using the supplied
journal class and a compatible LaTeX environment. Run pdfLaTeX twice for cross
references; the submitted `main.bbl` is preserved.

The submitted legacy journal preamble does not compile with this machine's
TeX Live 2025/current packages: it errors before the first table at a numbered
equation (`\veqno`). Removing the kernel rollback also fails with the legacy
class. The export preserves those supplied files rather than silently changing
the journal format. All seven generated tables compile and render successfully
in a standalone, table-only preview. This does not establish full-manuscript
compilation compatibility.

Figure regeneration uses full-KM survival curves, common-origin displacement
shares, saved transition counts and leave-one-out influence shifts. Numerical
plotting ledgers are saved alongside all four PDF files. It adds no new CIs and
does not claim pixel- or byte-identical PDFs across plotting-library versions.
Without `--regenerate-figures`, the exporter preserves the supplied figure assets.
Frozen results, original submitted documents and earlier publication bundles are
unchanged. No FRL, near-tie or post-referee input is required by the QF pipeline.
