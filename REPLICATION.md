# Frozen final-paper replication

**Historical FRL release:** this document describes the local v2 archive and
six-table FRL appendix. For the current QF V4 five-table appendix, see
[SCIENTIFIC_CORE.md](SCIENTIFIC_CORE.md) and
[QF_V4_PUBLICATION.md](QF_V4_PUBLICATION.md). The v2 archive predates the later
calendar/window, fixed-method and gap/perturbation additions; it is not a complete
QF V4 release. No public data deposit or DOI is claimed.

The submitted paper uses 17 U.S. industries as primary universe, 14 broader USD
country markets as secondary universe, and 30 industries as a granularity check.
Do not replace frozen French archives with current downloads.

## Fast reproduction from completed outputs (no empirical rerun)

1. Extract `portfolio_frozen_replication_v2.zip` into a new empty directory.
   It contains code, tests, the exact three raw archives and processed panels,
   completed run outputs, diagnostic inputs, and the submitted layout/prose ZIP.
2. Use Python **3.13.3** and the recorded numerical environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-frozen.txt
python -m pip install --no-deps --no-build-isolation -e .
$env:PYTHONPATH = 'src'
python -m portfolio_endpoint.replication_release --verify .
python -m pytest -q
python -m portfolio_endpoint.frl_publication
```

The corrected source bundle is written to `results/publication_final_repaired/`.
It contains `main.tex`, `online_appendix.tex`, `references.bib`, four figure PDFs,
exactly Tables 1--2 and A1--A6, CSV sources and `EXPORT_MANIFEST.json`.
The original submission and all baseline runs remain unchanged. Manuscript
assembly corrects the audited 12.1% to 12.0% rounding, nonexistent F.1--F.2
reference, and the Ledoit--Wolf covariance normalization wording. It does not
insert the later calendar/window checks into the paper.

With a TeX Live installation providing elsarticle and the packages named in the
source (including Courier font metrics for bibliography DOI formatting), compile
from the generated directory:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error online_appendix.tex
pdflatex -interaction=nonstopmode -halt-on-error online_appendix.tex
```

Binary-identical PDFs are not promised: TeX versions, PDF metadata and fonts may
differ. The goal is the same corrected scientific cells, figure inputs and final
publication architecture. The archive manifest validates every frozen release
input; generated figures retain full-precision sources until final display.

## Recorded empirical runs (expensive; not part of fast reproduction)

The commands below identify the completed designs, not instructions to rerun
them now. `replication/frozen_run_registry.json` records the exact inputs, seed,
resolved specifications, original manifests and completed replication counts.
All have gamma=5, cost=.0025, H=120 and h=12 unless the registry explicitly says
otherwise; no inner bootstrap was used.

```powershell
python -m portfolio_endpoint.study --run-name primary_17_definitive_B2000 --outer-reps 2000 --enhanced-sensitivities
python -m portfolio_endpoint.study --dataset replication_international_countries --run-name country_replication_B1000 --outer-reps 1000
python -m portfolio_endpoint.study --dataset replication_30_industry --run-name replication_30_B1000 --outer-reps 1000
python -m portfolio_endpoint.study --run-name primary_17_fixedblock12_B1000 --outer-reps 1000 --fixed-block-length 12
python -m portfolio_endpoint.study --run-name primary_17_fixedblock24_B1000 --outer-reps 1000 --fixed-block-length 24
python -m portfolio_endpoint.study --run-name primary_17_L36 --lookback 36
python -m portfolio_endpoint.study --run-name primary_17_L120 --lookback 120
python -m portfolio_endpoint.study --run-name primary_17_quarterly --rebalance-every 3
```

On the restored archive these directories are nonempty and the hardened runner
will refuse to overwrite them. To make independent new computations, use new
run names. Newly created bootstrap chunks can resume only under identical
resolved specifications, source/input identities and numerical versions.
Old manifests lack this resume identity: legacy runs fail closed rather than
being silently appended. Completed draws can always be read/exported unchanged.

Diagnostic construction modules are `portfolio_endpoint.diagnostics`,
`portfolio_endpoint.extension`, `portfolio_endpoint.country_bootstrap_report`,
and `portfolio_endpoint.near_tie`. Their saved outputs are included in the archive;
**do not rerun them for publication export**. The latter two summarize saved
results; diagnostics/extension may reconstruct paths and leave-one-out histories.

For fresh, non-paper data ingestion, `portfolio-ingest` now dispatches industry
CSV versus broader-country Dat correctly. The country rule remains uninterrupted
monthly USD Mkt observations beginning in January 1975. This command can download
mutable current data and must not be used to restore the frozen paper sample.

## Release availability and remaining external step

The ZIP is a local, versioned replication archive, not a permanent public deposit.
The author must choose a repository (e.g. a journal supplement or institutional
archive), confirm data redistribution terms, and publish the exact ZIP/manifest
with a permanent identifier. No repository deposit, DOI or long-term availability
is claimed by this repair. All software/input changes relative to the historical
run commits are classified as reporting or defensive validation corrections;
the audited portfolio rules, baseline estimates and saved draws are preserved.
