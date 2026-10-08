# Final validation report

## Scope

This report was regenerated from saved empirical and diagnostic outputs. No portfolio paths or bootstrap draws were created.

## Audit outcome

116/116 direct checks passed.

No computational or reporting discrepancy was found in the audited saved outputs.

## Important distinctions and limitations

- The original baseline survival summary is a censored KM estimate; the audit's headline S(12)/S(24) uses complete-follow-up origin cohorts. Common-origin robustness comparisons are separate and must not replace baseline estimates.
- The economic-material event is a first monthly CEQ gap strictly greater than 25 bp; it is not literal switching or an exact-month-12 event.
- Bootstrap CIs are percentile intervals from completed runs: stationary B=2,000 (17 industries), stationary B=1,000 (30 industries), and fixed circular-block B=1,000 sensitivity runs. They do not establish differences across specifications.
- The two industry universes share underlying equity histories and are not independent replications.

## Unavailable inference and recommendation

Formal claims about differences between baseline and L=36/L=120/quarterly survival or displacement profiles require paired outer-bootstrap differences. The minimum useful additional computation is a single paired stationary-bootstrap run (at least B=1,000) that evaluates the existing specifications on the same pseudo-histories. It was not run here.
