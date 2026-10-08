# QF paper-specific release cleanup and verification

## What changed

- The active exporter now imports `qf_tables`, not `final_publication` or the
  FRL builder. Only the appendix bodies used by V4 were extracted; no scientific
  specification or numerical table value changed.
- The obsolete near-tie input is no longer read or required by the QF pipeline.
- `qf_figures` regenerates all four V4 scientific figure objects from frozen
  survival, displacement, transition and leave-one-out diagnostics. CSV ledgers
  preserve the full-precision plotted values.
- `qf_release` uses an explicit 17-module allowlist, current tests and exactly
  49 frozen input files, plus template/audit/provenance metadata.
- The archival pyproject installs current scientific commands only. Legacy FRL,
  old publication, near-tie, post-referee and old release-builder modules and
  their entry points are omitted. Old generated publication directories, stale
  DATA_MANIFEST/EXECUTION_MANIFEST recipes and older release ZIPs are not included.
- Development history and historical audit snapshots are preserved. There was
  no Git history rewrite and no public upload in this cleanup.
- `scripts/reproduce_qf.py` is the single recommended reproduction command.

## Verification

1. The independently extracted QF table bodies exactly match the prior V4
   exporter reference for Tables 1, 2 and A1-A5.
2. A clean archive extraction with no legacy modules or near-tie input passed
   all 74 tests. Frozen archive files and all 49 input checksums were validated.
3. The one-command workflow regenerated seven tables with zero discrepancies
   across 342 printed numerical tokens and all four figure PDFs.
4. Transition counts were checked against the saved matrices; plot ledgers
   contain 203 KM rows, six common-origin displacement rows, 50 transition cells
   and 31 leave-one-out shifts. Complete-follow-up survival proportions are not
   substituted for the full-KM curves used in Figure 1.
5. Rendered figure panels were visually reviewed: labels, legends, scales and
   the Chemicals label are present without clipping or overlap. Figure 2 is
   descriptive common-origin winner-change/material-loss shares, not a new loss
   curve or newly computed confidence intervals. PDF byte identity is not claimed.

No portfolio construction, CEQ recomputation, endpoint/robustness run or bootstrap
was performed. Frozen outputs and submitted manuscript sources are unchanged.

## Limits before public deposit

This is a local candidate, not a Zenodo release or DOI. Software licensing needs
author approval; French data redistribution permission must be checked. The
historical B=5,000 / inner B=2,000 protocol record is explicitly labeled planned,
not executed; actual completed counts remain B=2,000/1,000 with no inner run.
The supplied journal preamble's local full-manuscript compilation limitation is
unchanged. Python/table/figure reproduction does not resolve that TeX issue.
