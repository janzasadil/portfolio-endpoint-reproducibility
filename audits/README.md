# Paper audit record

These are preserved snapshots of completed checks, not fresh analyses performed
when committing. `SNAPSHOT_MANIFEST.json` records original local paths and checksums.
The snapshots are intentionally tracked outside the ignored `results/` tree.

## Current QF V4

- `qf_v4/PAPER_CODE_AUDIT.md` and JSON: seven generated tables, 342 printed
  numerical tokens, no discrepancy; implementation/sample checks and four prose
  clarifications. Selector-minus-ensemble is a mean of decision-level differences.
- `qf_v4/table_numeric_audit.csv`: token-level comparison evidence.
- `qf_v4/EXPORT_MANIFEST.json`: saved inputs and template identity.
- `qf_v4/BUILD_VALIDATION.md`: 63 passing tests and successful standalone table
  proof; explicitly records failed local full-journal compilation.
- `calendar_window/ROBUSTNESS_AUDIT.md` and `validation.json`: completed calendar
  and H=60 checks, baseline reproduction and repeatability.
- `fixed_method/FIXED_METHOD_BENCHMARK_REPORT.md`: retrospective benchmarks.
- `gap_perturbation/GAP_PERTURBATION_REPORT.md`: saved-CEQ decomposition diagnostics.

## Historical records (not current publication architecture)

- `historical/SCIENTIFIC_CODE_AUDIT.md`: original independent FRL audit, including
  the then-observed **reproducibility failure**. Preserve the verdict; read the
  subsequent repair and current QF checks alongside it.
- `historical/REPAIR_REPORT.md`: closes local FRL exporter and input-workflow
  findings; permanent public deposit was not completed.
- `historical/audit_evidence.json`, `independently_reproduced_numbers.csv`, and
  `publication_cell_checks.json`: original independent numerical evidence.
- `historical/FINAL_VALIDATION_REPORT.md`: an earlier saved-output validation,
  using the publication architecture and sample distinctions then in scope.
- `historical/post_referee_extraction_audit.md`: earlier extraction audit.
- `historical/READABILITY_REPORT.md`: behavior-preserving readability verification.

Earlier test counts and appendix numbering belong to their respective reports;
they do not supersede the latest test suite / seven-table checks. These reports do
not claim that all bootstrap draws were independently rerun, that the current
QF companion archive is publicly available, or that external literature and
journal policies were independently verified. Historical report paths refer to
the original local artifacts; unchanged source/result files are not included here.
