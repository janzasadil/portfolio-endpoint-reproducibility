# Bounded calendar-phase and evaluation-window robustness audit

Completed 2026-10-06. Descriptive checks only: no bootstrap, retuning,
new portfolio rules, or changes to manuscript/publication/baseline outputs.

## Frozen implementation and artifacts

Repository HEAD: `a1ac0d5a5731d735ea0ad812d0e2b0aa6d3d8157`.
Existing implementation was used unchanged:

- `src/portfolio_endpoint/methods.py`: five headline portfolio rules.
- `src/portfolio_endpoint/engine.py::run_continuous_path`: 60-month estimation,
  monthly rebalancing, drifted holdings and multiplicative net-cost convention.
- `src/portfolio_endpoint/analysis.py::ceq`: annualized monthly mean minus
  gamma/2 times annualized sample variance (ddof=1), gamma=5.
- `analysis.py::endpoint_reproducibility`: fixed-order winner tie-breaking;
  retain the earlier winner and evaluate its shortfall on the displaced window.
- `study.py` and `bootstrap.py::outer_sensitivity_bootstrap`: original artifact
  construction and the meaning of the existing H5 bootstrap columns.

Baseline artifacts are `results/primary_17_definitive_B2000/endpoint_pairs.csv`
and `results/country_replication_B1000/endpoint_pairs.csv`, with their existing
run manifests and bootstrap files. Validated inputs are
`data/processed/ff_17_industry_value_weighted_monthly.csv` and
`data/processed/ff_international_country_markets_usd_monthly.csv`.
The existing final submitted manuscript in
`results/scientific_audit/submitted_source/main.tex` was read, not changed.

Inspection found no saved monthly candidate net-return paths sufficient for
these checks. Endpoint-level CEQs, summaries, and aggregate bootstrap metrics
cannot recover other terminal months or shorter evaluation windows. Therefore,
the same five continuous paths were reconstructed **once per universe** from
the frozen inputs with the existing engine, and cached here. The ensemble was
not rebuilt because neither requested check uses it. Paths are never restarted
at endpoints and are never estimated again when H or terminal month changes.
Both universes use cost=0.0025 per half turnover, h=12 and gamma=5.

Each cache's JSON records data/source digests, estimation choices and numerical
library versions; an incompatible cache is rejected rather than overwritten.
The new additive driver is `src/portfolio_endpoint/design_sensitivity.py`.
Run with the original Python 3.13 numerical environment and `PYTHONPATH=src`:

```powershell
& 'C:\Users\janza\AppData\Local\Programs\Python\Python313\python.exe' -m portfolio_endpoint.design_sensitivity
```

## Baseline gate and validation

The baseline gate ran before new sensitivity evaluations for each universe.
All existing baseline pair dates, winner identities, switch flags and CEQ/loss
columns matched (numeric tolerance 1e-12 in native units).

| Universe | December pairs | Winner changes | Loss >25 CEQ bp | Mean CEQ bp |
|---|---:|---:|---:|---:|
| 17 industries | 84 | 18 / 84 = 21.429% | 5 / 84 = 5.952% | 7.350208 |
| 14 countries | 36 | 6 / 36 = 16.667% | 4 / 36 = 11.111% | 10.552000 |

The requested primary publication rounding is exactly 84, 21.4%, 6.0%, 7.35 bp.

Validation additionally checked:

- uninterrupted, finite monthly paths (1,141 primary and 552 country OOS months);
- every earlier/later CEQ window contains exactly H observations;
- every displacement is exactly 12 positions **and** 12 calendar months;
- every saved CEQ equals the existing CEQ function applied to its declared slice;
- materiality uses native loss strictly greater than 0.0025, not rounded bp;
- rates are 100 times integer event counts divided by eligible counts;
- CEQ decimal returns are multiplied by 10,000 for bp;
- common-date rows intersect earlier terminal dates; they do not reset holdings;
- both checks run twice against identical streams, including a round-trip CSV
  reload; all summary and endpoint-level tables are exactly equal;
- automated suite: **23 passed**, including a new threshold-boundary regression
  test protecting strict >25 bp and count-based percentage calculation.

Machine-readable validation: `validation.json`. Detailed endpoint records:
`17_industries_H120_monthly_endpoint_pairs.csv`,
`17_industries_H60_monthly_endpoint_pairs.csv`, and the corresponding country files.

## Calendar-phase results

`calendar_phase_sensitivity.csv` contains 24 separate phase rows, with exact
counts, unrounded rates, mean/median/P90 and coverage dates. No phases were pooled.
`CALENDAR_PHASE_SENSITIVITY.md` supplies all extrema, phase medians and December
ranks, explicitly allowing tied ranks. Rankings ascend from lowest to highest.

For 17 industries, annual phases have 84–85 pairs:

- literal switching: 20.24% (April) to 29.76% (February);
- loss >25 bp: 5.95% (January/October/November/December) to 10.71%
  (March/May/August);
- mean loss: 5.09 bp (January) to 11.83 bp (February).

December ranks second-lowest for switching, tied lowest for material-loss rate,
and fifth-lowest for mean loss. It is a relatively conservative phase, not the
lowest primary mean-loss phase.

For countries, phases have 35–36 pairs:

- switching: 16.67% (December) to 28.57% (April/September);
- loss >25 bp: 8.57% (April) to 22.86% (July);
- mean loss: 10.55 bp (December) to 28.26 bp (August).

December is lowest for country switching and mean loss, and second-lowest for
material-loss rate. It understates typical phase levels in this secondary sample.
In **all twelve phases of each universe**, literal winner changes remain more
frequent than losses above 25 bp. These are descriptive comparisons, not evidence
of statistically unusual December behavior.

## Evaluation-window results and coverage

The H=60 check retains the original 60-month estimation lookback and the same
continuous net returns. Only evaluation-window slices change.

| Universe / sample | H120 n | H60 n | Switching: H120 to H60 | Loss >25: H120 to H60 | Mean bp: H120 to H60 |
|---|---:|---:|---:|---:|---:|
| 17 / all eligible | 84 | 89 | 21.43% to 34.83% | 5.95% to 19.10% | 7.35 to 34.57 |
| 17 / common dates | 84 | 84 | 21.43% to 34.52% | 5.95% to 17.86% | 7.35 to 35.00 |
| Countries / all eligible | 36 | 41 | 16.67% to 31.71% | 11.11% to 21.95% | 10.55 to 37.01 |
| Countries / common dates | 36 | 36 | 16.67% to 30.56% | 11.11% to 22.22% | 10.55 to 40.11 |

The common dates are 1941-12 through 2024-12 for industries and 1989-12 through
2024-12 for countries. H60 adds five earlier December dates in each full sample:
1936-12 through 1940-12 and 1984-12 through 1988-12, respectively.

The change is primarily window-length sensitivity, not the extra early dates:
both versions give the same qualitative ordering and substantially larger losses.
Removing the extra dates changes the H60 primary mean by +0.43 bp and the country
mean by +3.10 bp. It changes H60 material rates by -1.24 and +0.27 percentage points.
All four comparisons retain zero median loss, but tail losses rise sharply;
exact P90s and changes in rates/means are in `EVALUATION_WINDOW_SENSITIVITY.md`.

An important qualification: in the primary full H60 sample, **17 of 31 switches
(54.8%)** exceed 25 bp, versus 5 of 18 (27.8%) at H120. On common dates it is
15 of 29 (51.7%). Thus the claim that *most switches are economically immaterial*
does not generalize to H60, even though material events remain less frequent than
literal changes over all eligible origins. The two event definitions are nested:
a material endpoint loss implies a literal winner change. Their strict frequency
gap is informative descriptively but should not be oversold as independent
inferential evidence.

## Bootstrap availability, without launching computation

`bootstrap_artifact_inventory.json` lists exact files and available columns.
The completed primary enhanced B=2,000 bootstrap already saves H5 (=H60) mean,
median, P90, switching, origin counts and paired differences from baseline.
Existing all-eligible primary H60 inference for those quantities can be summarized
without any new portfolio computations. No intervals were computed for this task.

Missing quantities include the strict material-loss event rate and common-date
statistics. Replication-level paths/endpoint losses were not saved, so aggregate
means/quantiles cannot reconstruct these. The completed country B=1,000 file has
no H5 outputs. Obtaining those missing bootstrap quantities would require replaying
the seeded pseudo-histories and reconstructing paths, broadly the dominant cost
of a full bootstrap; omitting unrelated post-processing would save some work.
No claim of an exact runtime estimate is made.

## Decision-oriented summary

1. **Is December unusual relative to the other eleven phases?** In the primary
   sample it is low on switching/material rates but not extreme on mean loss.
   In countries it is the lowest switching and mean-loss phase. December is
   conservative, especially internationally; this is not a significance claim.
2. **Does ordinal-versus-economic separation hold across phases?** Yes: literal
   changes exceed >25-bp losses in all twelve phases in both universes.
3. **Does it survive H120 to H60?** Yes, for both full and common-date samples;
   however, materially costly changes are much more frequent at H60.
4. **How much changes?** On common dates, primary switching increases 13.10 pp,
   material losses 11.90 pp and mean loss 27.65 bp (7.35 to 35.00). Country changes
   are +13.89 pp, +11.11 pp and +29.56 bp (10.55 to 40.11). Full-sample increases
   in mean loss are +27.22 and +26.46 bp, respectively.
5. **Would either check materially alter the central claim?** The manuscript's
   narrow claim that changing a winner need not imply a material loss survives.
   Magnitude and calendar/window qualifications are important. An unrestricted
   claim of uniformly small losses, or mostly immaterial switches across window
   lengths, would not survive these checks. No manuscript edits were made.
6. **Is additional bootstrap scientifically necessary?** Not for these bounded,
   explicitly descriptive sensitivity checks. Existing primary H60 draws already
   support some uncertainty summaries if requested. Formal claims about changes
   in material-loss rates or common-date effects would need suitable additional
   dependence-aware inference; no new bootstrap is needed merely to report these
   point-estimate sensitivities.
