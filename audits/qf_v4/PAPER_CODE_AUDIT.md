# QF V4 paper-code consistency audit

Generated all seven tables from frozen outputs. Compared 342 printed numerical tokens (including numerical row labels) across 15 table bodies: 0 discrepancies.

## Verified

- Main endpoint counts, strict >25-bp rates, conditional losses, gap/perturbation medians, and all printed bootstrap bounds.
- Prospective counts 75/27, hit rates 38.7%/25.9%, regret 109.12/48.25 bp, retrospective fixed-method benchmarks, and arithmetic mean selector-minus-ensemble differences -10.93/+58.11 bp.
- Full-eligible versus common-date displacement samples; all twelve calendar phases; H=60 common-date results.
- Specification-specific KM medians and complete-follow-up 0/25/50-bp survival slices are distinct and correctly labeled.
- CEQ sample variance, frozen exact tie priority, continuous holdings, t-to-t+1 timing, half-L1 turnover, multiplicative net costs, no entry turnover, and separately traded ensemble agree with the implementation.
- Sample covariance uses divisor L-1; the centered Ledoit-Wolf empirical covariance uses divisor L. Solver tolerances agree with Appendix F.
- Existing bootstrap counts/block lengths and the same decision-level mean within ordinary/enhanced bootstrap replications.

## Exact specification sample sizes

| Specification | Endpoint pairs | Full-KM origins | Median (months) |
|---|---:|---:|---:|
| 17_baseline | 84 | 85 | 31 |
| 17_L36 | 86 | 87 | 14 |
| 17_L120 | 79 | 80 | 13 |
| 17_quarterly | 84 | 85 | 18 |

## Wording/implementation clarifications (not changed automatically)

- The decomposition medians in Results 3.1 are conditional on a winner change, as Table 1 Panel B states. Make that conditioning explicit in the prose; unconditional medians include structural zeros.
- Table A1 Panel A uses specification-specific eligible samples and full-sample KM medians, not the earlier 80-common-origin analysis. Adding those sample definitions/counts to its note would improve transparency.
- The corrected Politis-White implementation additionally bounds block lengths to [2, floor(sqrt(T))] and rounds upward; Appendix E gives the realized lengths but does not state this implementation detail.
- The international Mkt series is the broader value-weighted USD series with all four valuation ratios not required; its market coverage depends on B/M availability. Do not describe it as every listed stock in a national index.

## Scope and preservation

No numerical inconsistency was found in the submitted tables.
The manuscript prose, journal class, bibliography, and four figure assets are copied from the V4 ZIP without scientific edits. Figures remain supplied assets; do not assume this exporter regenerates them if data change.
Original Downloads files, earlier publication outputs, and frozen empirical run directories are unchanged. No portfolio construction, endpoint/robustness analysis, or bootstrap ran. Only lightweight saved-output aggregation and percentile quantiles were evaluated.
This is a paper-code audit, not an independent check of external literature, journal policies, author declarations, or every pixel of the supplied figures.

Machine-readable evidence: table_numeric_audit.csv, PAPER_CODE_AUDIT.json, EXPORT_MANIFEST.json, and sources/publication_table_bodies.json.
