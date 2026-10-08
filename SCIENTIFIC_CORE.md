# Scientific core of the QF V4 paper

This repository contains the paper's Python implementation, tests, frozen design,
recorded numerical environment, and audit snapshots. It does not contain mutable
raw downloads, completed bootstrap draws, temporary inspection scripts, generated
manuscript packages, or a claim that the frozen data are publicly deposited.

## Paper-to-code map

| Scientific object | Python implementation |
|---|---|
| French monthly inputs, uninterrupted calendars and broader country Mkt selection | `ingest.py`, `countries.py` |
| Five long-only portfolio methods and numerical tolerances | `methods.py` |
| Continuous drifted holdings, rebalancing, turnover, net costs and ensemble path | `engine.py` |
| CEQ, terminal-date endpoint loss, winner persistence, KM and annual ex ante selection | `analysis.py` |
| Primary, country and 30-industry runs; lookback/quarterly alternatives | `study.py` |
| Stationary and fixed circular-block bootstrap, paired inexpensive sensitivities | `bootstrap.py` |
| Survival/materiality validation and implementation sensitivities | `diagnostics.py` |
| Method-conditioned diagnostics, transitions, influence and displacement | `extension.py` |
| Calendar phases and H=60 common-date sensitivity | `design_sensitivity.py` |
| Initial-gap / relative-perturbation decomposition from saved CEQs | `gap_perturbation.py` |
| Retrospective fixed-method and future-winner base-rate benchmarks | `fixed_method_benchmark.py` |
| QF V4 Tables 1, 2 and A1-A5; printed-value and implementation checks | `qf_publication.py`, `qf_tables.py` |
| All four QF figure PDFs and full-precision plotting ledgers | `qf_figures.py` |
| Paper-specific frozen archive and input/file verification | `qf_release.py`, `scripts/reproduce_qf.py` |

All modules are under `src/portfolio_endpoint/`. The one-command archival workflow
regenerates figures from saved diagnostics, without reconstructing portfolios or
invoking old publication builders. The exporter also supports a template-figure
preservation mode for comparison. Legacy reporting,
near-tie and post-referee modules are retained in the development repository for
historical dependencies and provenance, but omitted from the QF archival package.
They are not promoted as additional V4 publication results. The old FRL
release utility remains available but is not a current QF release builder.

## Installation and verification

Python 3.11+ is supported by project metadata. The audited frozen numerical
environment used Python 3.13.3; exact package versions are recorded in
`requirements-frozen.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-frozen.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m pytest -q
```

The current suite has 74 passing tests. It exercises estimators, timing, costs,
calendar validation, CEQ/tie/threshold rules, bootstrap behavior, safe resume,
diagnostics, publication formatting and tracked audit-snapshot integrity.
Tests do not regenerate all 6,000 saved
bootstrap replications or certify statistical inference beyond the implemented
procedure. See [audits/README.md](audits/README.md) for additional recorded checks.

## Frozen design versus completed computation

`config/experiment.yaml` preserves the original planned B=5,000 / inner B=2,000
protocol values. Do not mistake these for completed counts. The actual published
primary run used outer B=2,000; countries, 30 industries and each 12/24-month
circular-block sensitivity used B=1,000. No inner bootstrap was run.

`replication/frozen_run_registry.json` is an unchanged provenance snapshot from
the earlier frozen v2 archive, recording the completed runs and original
manifests. It is not a manifest asserting that archived source hashes equal this
later code commit. Subsequent changes include defensive validation, the corrected
PW fallback, readability, added requested diagnostics, and publication export;
existing frozen empirical outputs were preserved. Historical audit/repair
reports explain these distinctions.

## What is still needed for exact paper-table reproduction

Follow [QF_V4_PUBLICATION.md](QF_V4_PUBLICATION.md). It requires the frozen result
directories listed by the exporter (including later calendar/window and
diagnostic additions), the original data/sample information, and the submitted
V4 source ZIP. Existing completed draws are summarized; no bootstrap is needed
to export tables. The local v2 FRL archive alone lacks some of those later files.

The source ZIP supplies layout/prose and static figure assets only: generated
numerical table bodies come from saved results. On the frozen local inputs, all
342 printed numerical tokens in the seven V4 tables matched the supplied source.
The supplied journal template has a local LaTeX compatibility limitation;
standalone tables compiled successfully, but full QF compilation is not verified
on this machine. See the current build audit.

A paper-specific local QF V4 archive can be built with:

```text
python -m portfolio_endpoint.qf_release --source-zip PATH_TO_V4_SOURCE.zip
```

It must be
deposited only after licensing and redistribution terms are checked. No DOI or public availability
is implied by committing this code. Raw inputs, generated results and archives
remain ignored rather than being silently added to Git.
