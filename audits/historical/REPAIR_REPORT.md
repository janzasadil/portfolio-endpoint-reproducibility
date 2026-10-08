# Reproducibility repair and verification

Date: 2026-10-06. Follow-up to `results/scientific_audit/SCIENTIFIC_CODE_AUDIT.md`.
The original audit and submitted ZIP remain unchanged. This is a correction
report, not a retroactive replacement of the audit verdict.

## Outcome

The final-paper exporter and local frozen-release workflow are repaired.
The corrected package can be regenerated from an isolated extracted release
without downloading current French data, reconstructing portfolio histories,
or launching bootstraps. Its table architecture matches the final submission:
Tables 1--2, appendix Tables A1--A6, and four referenced figures.

**Remaining external step:** deposit the final replication ZIP in an author-chosen
permanent repository, confirm redistribution terms, and insert its persistent
reference where appropriate. No public availability, DOI, or hosting is claimed.
The verification used an isolated directory with the existing audited numerical
environment, not a newly provisioned machine or a fresh 6,000-draw bootstrap.

## Findings closed locally

| Audit item | Repair | Verification |
|---|---|---|
| M1 final exporter mismatch | `final_publication.py` rebuilds all table data bodies from canonical outputs; submitted templates supply layout only. Near-tie A3 is included; method diagnostics are A4, bootstrap A5, implementation A6. Table 1 includes strict materiality and switch-conditioned results. Granularity includes 17 and 30 industries; country equal-weight count is 0. | All 267 audited numeric cells match independent audit expectations, including corrected rounding. Eight floats, no duplicate appendix tables. |
| M2 missing frozen bundle/workflow | `replication_release.py`, `requirements-frozen.txt`, `REPLICATION.md`, and corrected README. Release includes all three raw/processed panels, completed draws/diagnostics, code/tests, submitted layout ZIP, input digest manifest, and resolved registry for eight runs. | 171 manifest-listed files validated; isolated extraction exported successfully without Downloads-folder dependencies or network. Permanent deposit remains external. |
| m1 double rounding | No intermediate rounding before table formatting or figure data; percentages format directly from native proportions. Generated main text and Table A2 report 10/83 as 12.0%, and 11/83 as 13.3%. | Threshold/display tests and independent cell comparison pass. |
| m2 PW fallback | Missing insignificant-autocorrelation run now selects maximum bandwidth. | Persistent-trend regression returns 14, formerly 5. Frozen selected lengths remain 34 / 6 / 34 for 17 / countries / 30. No existing bootstrap requires rerunning. |
| m3 unsupported bootstrap options | Quarterly inference and enhanced/fixed-block combinations fail explicitly before filesystem access or computation. Quarterly point estimates remain supported. | Parameterized CLI guard tests pass. |
| m4 unsafe resume | New manifests record full resolved design, input/source digests, numerical environment and selected block length. Resume validates identity, column family, contiguous ordered IDs and fixed block rule before writes or portfolio construction. Fresh runs refuse nonempty output directories. | Identity, legacy-manifest, registry-gap and block-mismatch tests pass. Legacy completed runs remain readable/exportable, but fail closed if someone attempts to append without identity metadata. |
| m5 weak monthly validation | Industry parser/engine reject calendar gaps, duplicates, non-month-end dates and nonfinite observations. Country records remain a list until duplicate-date detection, avoiding dictionary collapse. Default ingestion dispatches country Dat parsing correctly. | Missing-month, duplicate-country, engine-before-estimation and country-dispatch tests pass. All three frozen parser outputs still match processed panels within 1e-15. |
| m6 covariance convention | Corrected generated main source distinguishes Sample GMV's divisor-L-1 S from the centered divisor-L C used inside Ledoit--Wolf. A6 notes the library convention. | Frozen numerical estimator unchanged; generated formula/notes inspected. |
| m7 nonexistent reference | Generated manuscript cites existing Online Appendix Section F and Table A6 instead of F.1--F.2. | Final LaTeX compile has no unresolved references. |

Country bootstrap narrative is now generated from saved statistics and actual
pair/decision counts rather than manually entered numerical sentences.

## Delivered artifacts

- `release/FRL_REPAIRED_SOURCE.zip`: corrected manuscript/appendix sources,
  compiled PDFs, figures, CSV sources, export manifest and check results.
- `release/portfolio_frozen_replication_v2.zip`: final portable replication archive,
  5,533,006 bytes; SHA-256
  `84f50a7c2b5d727233104a47ac6f608789ad31aacfe1632530c00c528cdd4e47`.
- `results/publication_final_repaired/`: unpacked corrected publication package.
- `REPLICATION.md`: restoration, verification, export and compilation instructions.

The v1 ZIP is an earlier local packaging check, superseded by v2. Use **v2** for
the frozen release. The original `results/publication`, `results/publication_frl`,
empirical run directories and submitted archive were not overwritten.

## Verification evidence

1. Full tests: **35 passed** in the project and extracted-release directory.
2. `INDEPENDENT_CELL_CHECKS.json`: 267 numeric cells across Tables 1--2/A1--A5,
   compared with independently reconstructed audit expectations; all match.
   A6 uses exact validated calendar dates, asset counts and saved analysis counts.
3. `CLEANROOM_CHECKS.json`: all 31 table/manuscript/bibliography/figure-image/source
   artifacts match byte-for-byte between project export and isolated v2 export.
4. Frozen raw parsers match the 1,201x17, 1,201x30 and 612x14 processed panels,
   including calendar and asset order. Default country ingestion is separately
   exercised on a synthetic Dat archive without downloads.
5. Both documents compile under local TeX Live 2025, with final logs containing
   no unresolved-reference, font-shape or overfull-box warnings. Main PDF: 9 pages;
   appendix: 7 pages. All pages and four regenerated figure PDFs were rendered;
   contact sheets and full-resolution key table pages were visually reviewed.
6. Installed missing local TeX packages to complete verification: elsarticle,
   microtype, needspace, placeins and Courier. Numerical Python packages and
   scientific data were not changed.

PDF byte identity is not claimed because TeX versions, metadata and font builds
can differ. The clean-directory comparison covers exact TeX, numerical CSV/JSON,
and rendered figure PNG content. The final source ZIP excludes staging tables
and LaTeX auxiliary/log files; there is only one intended float per table ID.

## Scope and cautions

No raw scientific input, frozen specification, saved portfolio estimate or
bootstrap draw was changed. No new empirical analysis was run in this repair.
The post-review calendar/window checks were not inserted into the manuscript.
The hardening changes preserve valid frozen-data behavior while rejecting unsafe
future invocations. The permanent archive step still needs author guidance;
this report does not certify future hosting or fresh full-bootstrap replication.
