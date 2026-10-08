# Portfolio Endpoint Reproducibility

Scientific code for the portfolio-method terminal-date reproducibility paper,
using fixed industry and broader USD country-market return panels. The current
publication target is **QF V4**, with two main tables and five appendix tables.
Start with [SCIENTIFIC_CORE.md](SCIENTIFIC_CORE.md) for the paper-to-code map and
[QF_V4_PUBLICATION.md](QF_V4_PUBLICATION.md) for table generation.

Frozen data and completed simulations are not stored in Git. A code checkout
alone does not reproduce the paper's tables: it also needs the frozen companion
inputs/results and V4 layout ZIP. Do not substitute fresh French downloads.
The older local FRL archive is documented in [REPLICATION.md](REPLICATION.md);
it is not a complete QF V4 release or a public deposit.

## Frozen design

- **Primary universe:** 17 Fama–French industry portfolios, monthly value-weighted returns.
- **Secondary universe:** 14 developed-country broader USD market portfolios.
- **Granularity check:** 30 Fama–French industry portfolios, monthly value-weighted returns.
- **Estimation window:** 60 months (configured in `config/experiment.yaml`).
- **Source:** Kenneth R. French Data Library. The data loader extracts only the monthly *value-weighted* block and converts reported percentages to decimal returns.

The French library changed its underlying CRSP return format from FIZ to CIZ beginning with its January 2025 release. Every downloaded archive and derived panel is therefore checksum-recorded in `DATA_MANIFEST.md`; do not replace a frozen input in place.

## Quick start

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
portfolio-ingest
pytest
```

`portfolio-ingest` downloads a configured archive only when it is absent from `data/raw/`, writes decimal monthly return panels to `data/processed/`, and updates the manifest. Existing raw archives are never overwritten. Raw data and generated outputs are intentionally ignored by Git.

Run the minimum primary analysis with:

```powershell
$env:PYTHONPATH = 'src'
python -m portfolio_endpoint.study
```

It writes endpoint, survival, selector, and summary outputs under `results/primary_17_industry/`. For a resumable 2,000-rep outer bootstrap in two 1,000-rep chunks:

```powershell
python -m portfolio_endpoint.study --run-name primary_17_B2000 --outer-reps 1000
# After the first chunk finishes:
python -m portfolio_endpoint.study --run-name primary_17_B2000 --outer-reps 1000 --resume
```

Draws are checkpointed every 10 replications. Use `--outer-reps 5000` only for the full (slow) protocol bootstrap.

## Final reporting bundle

For the newer QF V4 manuscript (two main tables and five appendix tables), use
the saved-output exporter documented in [QF_V4_PUBLICATION.md](QF_V4_PUBLICATION.md).
The FRL command below preserves the older publication architecture.

After completed empirical and diagnostic runs are present locally, regenerate the
publication bundle without rebuilding portfolio paths or launching a bootstrap:

```powershell
$env:PYTHONPATH = 'src'
python -m portfolio_endpoint.frl_publication
```

This requires `replication/frozen_source.zip` from the frozen release and writes
the final two main tables, six appendix tables, figures and manuscript sources
to `results/publication_final_repaired/`. To use the author's submitted ZIP
directly, add `--source-zip PATH`. No portfolio paths or bootstrap draws are rebuilt.
The older `portfolio_endpoint.reporting` module is a legacy industry-only bundle,
not the exporter for the final paper. See [REPLICATION.md](REPLICATION.md) for
the frozen numerical environment, five completed bootstrap runs and compilation.

## Layout

- `config/` — fixed experimental choices and data locations.
- `src/portfolio_endpoint/` — ingestion and future portfolio-method implementation.
- `tests/` — parser and protocol tests.
- `data/raw/` — immutable source archives, local only.
- `data/processed/` — derived panels, local only.
- `results/` — generated tables and figures, local only.

## Data provenance

See [DATA_MANIFEST.md](DATA_MANIFEST.md). The official library documents both the industry construction and the current-return methodology at the [17 Industry detail page](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_17_ind_port.html) and [Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
