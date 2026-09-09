# Portfolio Endpoint Reproducibility

Reproducible empirical study of portfolio endpoint methods using fixed, synchronized Fama–French industry-portfolio return panels.

## Frozen design

- **Primary universe:** 17 Fama–French industry portfolios, monthly value-weighted returns.
- **Replication universe:** 30 Fama–French industry portfolios, monthly value-weighted returns.
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

It writes endpoint, survival, selector, and summary outputs under `results/primary_17_industry/`. Add `--outer-reps 5000` only for the full (slow) protocol bootstrap.

## Layout

- `config/` — fixed experimental choices and data locations.
- `src/portfolio_endpoint/` — ingestion and future portfolio-method implementation.
- `tests/` — parser and protocol tests.
- `data/raw/` — immutable source archives, local only.
- `data/processed/` — derived panels, local only.
- `results/` — generated tables and figures, local only.

## Data provenance

See [DATA_MANIFEST.md](DATA_MANIFEST.md). The official library documents both the industry construction and the current-return methodology at the [17 Industry detail page](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_17_ind_port.html) and [Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
