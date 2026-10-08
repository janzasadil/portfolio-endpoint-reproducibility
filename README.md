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

The frozen numerical environment uses Python 3.13.3.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-frozen.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m pytest -q
```

With the paper-specific frozen companion package restored, reproduce the QF tables
and all four figures with one command:

```powershell
python scripts/reproduce_qf.py
```

This validates frozen input identities and regenerates seven tables/four figures
from saved outputs; it does not run an empirical analysis or bootstrap. The local
QF archive is a candidate pending licensing/data-redistribution checks, not a DOI
deposit. See [replication/QF_RELEASE_README.md](replication/QF_RELEASE_README.md).

`portfolio-ingest` is for fresh-data work only, not restoration of the frozen
paper sample. Data and generated research outputs are intentionally ignored by Git.

## Final reporting bundle

For the newer QF V4 manuscript (two main tables and five appendix tables), use
the saved-output exporter documented in [QF_V4_PUBLICATION.md](QF_V4_PUBLICATION.md).
The FRL command below preserves the older publication architecture.

Historical FRL/reporting utilities remain in the development repository, documented
in [REPLICATION.md](REPLICATION.md), but are excluded from the paper-specific QF
archive. QF generation no longer depends on those utilities or old near-tie results.

## Layout

- `config/` — fixed experimental choices and data locations.
- `src/portfolio_endpoint/` — scientific implementation and publication generation.
- `tests/` — parser and protocol tests.
- `data/raw/` — immutable source archives, local only.
- `data/processed/` — derived panels, local only.
- `results/` — generated tables and figures, local only.

## Data provenance

See [DATA_MANIFEST.md](DATA_MANIFEST.md). The official library documents both the industry construction and the current-return methodology at the [17 Industry detail page](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_17_ind_port.html) and [Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
