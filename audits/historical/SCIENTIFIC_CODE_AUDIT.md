# REPRODUCIBILITY FAILURE

**Verdict scope:** the strict requirement that a clean checkout regenerate the exact final manuscript package is not currently met. The empirical computations audited here reproduce the frozen results. This verdict concerns the final publication exporter, release inputs, and documented workflow; it is not evidence that the headline scientific conclusions are wrong.

Audit date: 6 October 2026. Submitted manuscript: `C:/Users/janza/Downloads/FRL_FINAL_SOURCE.zip`. Production source and frozen scientific outputs were not edited. Audit scripts, regenerated comparison files, and this report are confined to `results/scientific_audit/`.

## Audit method and limits

- Parsed the final `main.tex`, `online_appendix.tex`, all eight table fragments, and the compiled PDFs in the supplied ZIP. Rendered and inspected the four referenced figure PDFs. The two additional ordinal/material PDFs in the archive are unreferenced legacy artifacts.
- Parsed each frozen raw ZIP afresh and compared its returns and asset order with the processed panel. All calendars were independently checked for uninterrupted monthly coverage.
- Rebuilt all three baseline portfolio histories, including each ensemble, under the package versions recorded in the final run manifests. Independently computed endpoint CEQs, winners, losses, annual selections, monthly first failures, and Kaplan--Meier curves with separate NumPy calculations.
- Rebuilt the L=36, L=120, and quarterly histories and checked gamma, cost, and material-threshold sensitivities. Independently reconstructed the common-origin survival calculation.
- Recomputed every reported percentile interval from the complete saved bootstrap draws. Checked all five draw registries for sequential, unique replication IDs and fixed block lengths. Reconstructed replication 0 for each of the five bootstrap designs and the final enhanced primary replication, 1999.
- Re-executed the publication generator with writes redirected to the audit directory. Compared its output organization and values with the submitted source. Original publication artifacts were preserved.
- Ran the existing test suite: **22 passed**. Additional audit examples checked no-look-ahead timing, known diagonal-covariance GMV weights, equal ERC risk budgets, exact-tie priority, block-length fallback, and parser edge cases.
- Rebuilt all **31** leave-one-out candidate histories (17 industry omissions and 14 country omissions); endpoint means, winner-change rates, eligible counts, and complete-follow-up S(12) values all match the saved files. Exact influence shifts plotted in Figure A2 are therefore verified for every omission.

**Limit:** the complete 6,000 bootstrap replications were not regenerated. All reported intervals were independently reconstructed from their full saved draw files, and representative full-procedure replications were regenerated. An exhaustive fresh bootstrap is a separate multi-day verification, not a completed part of this audit. No claim of mathematical validity of bootstrap inference for nonsmooth winner statistics is made beyond checking the implemented procedure and the manuscript's stated interpretation.

The matched computational environment is Python 3.13.3, NumPy 2.3.5, pandas 2.3.3, SciPy 1.16.3, and scikit-learn 1.8.0. Manifest commits differ between the three completed runs; current baseline behavior was verified numerically rather than presumed equivalent from commit labels.

## Findings by severity

### Critical

None identified in the audited published computations.

### Major M1: the final publication package has no matching exporter

1. **Locations:** `src/portfolio_endpoint/frl_publication.py:35`, `:96`, `:119`, `:155`; `README.md:45`; submitted `online_appendix.tex:47` through `:100`.
2. **Observed behavior:** the final manuscript contains Tables 1--2 and A1--A6. `frl_publication.main` emits an earlier five-table appendix. Its Table 1 lacks the final material-loss and switch-conditioned rows; it has no final near-tie Table A3; method-conditioned results are emitted as A3 instead of A4; bootstrap results are emitted as A4 instead of A5; implementation details are emitted as A5 instead of A6. The final granularity panel also has two rows whereas the exporter emits only the 30-industry row. The empty country equal-weight group is exported with `--` for its count, while the final table correctly reports 0. The README's final-report command invokes the older `reporting.py`, which uses 17 and 30 industries rather than the final 17-industry/country main-text pairing. `country_bootstrap_report.py` also contains manually written numerical narrative in addition to its data-derived table.
3. **Expected behavior:** a documented final exporter should generate the exact final table organization and numerical cells from the frozen outputs, including near-tie summaries, and identify the intended source files.
4. **Consequence:** an investigator following the current reporting instructions obtains a different publication bundle. The final package cannot currently be independently regenerated through the documented exporter alone.
5. **Existing outputs affected:** publication organization, captions, sample-count presentation, and generation provenance. Independently checked underlying published values are correct except the rounding issue below.
6. **Minimal correction:** synchronize the exporter to the supplied final LaTeX architecture, derive counts/dates/conditional rows from canonical files, add the final near-tie table, and document the exact command sequence. Preserve the frozen estimands.
7. **Recomputation:** table/figure export and manuscript assembly only; no new portfolio analysis or bootstrap is necessary.

### Major M2: a clean-checkout replication needs an unavailable frozen-input/workflow bundle

1. **Locations:** `.gitignore:9` onward; `README.md:16`--`:43`; `config/experiment.yaml:33`; `src/portfolio_endpoint/ingest.py:61`, `:79`, `:98`; `pyproject.toml:12`; `study.py:_run_manifest` at `:41`.
2. **Observed behavior:** Git tracks only directory placeholders for raw data, processed data, and outputs. The README downloads mutable current French files, not a retrievable versioned frozen archive. The final run names and complete export sequence are not documented, and the dependency requirements have lower bounds only. Additionally, plain `portfolio-ingest` selects every configured dataset and applies the industry CSV extractor to `F-F_International_Countries.zip`, which contains `.Dat` files. The actual archive produces `ValueError('Expected one CSV ... found []')`. The separate `portfolio-countries` parser is correct but is not included in that default workflow. Run manifests record seed, versions, dataset, and Git commit, but omit the full resolved specification, CLI overrides, and input identities.
3. **Expected behavior:** a clean-checkout recipe should identify and obtain the frozen input snapshots, dispatch each source format correctly, reproduce all final run specifications, and provide the recorded numerical environment.
4. **Consequence:** downloading today's inputs can change dates, denominators, and estimates; the documented default pipeline fails at the country dataset. A clean checkout does not reproduce the submitted paper as supplied.
5. **Existing outputs affected:** none of the frozen local outputs. Their raw/processed industry checksums match the tracked manifest; the country raw checksum matches its saved country-selection audit.
6. **Minimal correction:** supply a versioned replication archive containing the frozen data or a reliable acquisition reference, full resolved configurations, recorded environment requirements, and a country-aware ingestion recipe. Update the README to name the five final bootstrap runs and required diagnostic/export steps. The manuscript's promised permanent archive is an appropriate place for this bundle.
7. **Recomputation:** no empirical rerun is required to fix packaging; a clean-room verification using the existing frozen inputs is required before claiming end-to-end replication.

### Minor m1: double rounding changes a displayed percentage

1. **Locations:** `frl_publication.py:69`--`:92`; submitted `tables/table_A2.tex:17`; submitted `main.tex:197`.
2. **Observed behavior:** the 17-industry common-date 24-month material-loss count is **10/83**. Its exact rate is **12.0481927711%**, which rounds directly to **12.0%** at one decimal. The submitted table and main text say **12.1%**. The exporter first rounds percentages to two decimals, then formats to one, producing 12.1%. The same mechanism exports the six-month U.S. switch rate as **13.2%** instead of **13.3%**; the submitted manuscript has already corrected that latter value. Figure 2 also consumes the prematurely rounded two-decimal shares.
3. **Expected behavior:** retain full precision through computation and plotting; round once to the final display precision.
4. **Consequence:** a 0.1-percentage-point display discrepancy, without changing counts, ordering, or substantive interpretation.
5. **Existing outputs affected:** the 12.1% in submitted Table A2 and Results Section 3.3; the old exporter also generates the 13.2% discrepancy. Underlying displacement CSVs are correct.
6. **Minimal correction:** use full-precision displacement data for plotting and format copies once for tables. Change the two submitted 12.1% occurrences to 12.0%.
7. **Recomputation:** export/manuscript corrections only; none of the portfolios or bootstrap draws.

### Minor m2: corrected-PW fallback is incorrect for an untriggered branch

1. **Location:** `bootstrap.py:60`, `corrected_pw_stationary_block_length`.
2. **Observed behavior:** `insignificant_start or 1` collapses `None` to 1, forcing bandwidth 2 if no run of insignificant autocorrelations is found. The corrected reference algorithm instead uses `m_max` in that case. A finite, trending 200-point synthetic series produces bounded block length **5** under the project code versus **14** with the correct fallback.
3. **Expected behavior:** distinguish `None` from a detected lag and use the maximum search bandwidth when the detection fails. See the [reference implementation](https://github.com/bashtage/arch/blob/main/arch/bootstrap/base.py), `_single_optimal_block`, which documents the Politis--White rule and Patton--Politis--White correction.
4. **Consequence:** the function can select an incorrectly short block length for another input series.
5. **Existing outputs affected:** **none** of the three published universes. Detected lags are non-null in all six selector inputs. Independent values are 3/34 for 17 industries, 3/6 for countries, and 2/34 for 30 industries; their maxima are the reported **34/6/34**.
6. **Minimal correction:** correct the fallback only and add a behavioral test whose autocorrelation search has no insignificant run.
7. **Recomputation:** no published bootstrap needs rerunning because the corrected branch gives identical lengths for the frozen data.

### Minor m3: quarterly point estimates can be paired with monthly bootstrap draws

1. **Locations:** `study.py:77`, `:107`--`:114`; `bootstrap.py:122`, `:151`, `:196`, `:219`.
2. **Observed behavior:** `--rebalance-every 3` reaches the original-sample path builder, but it is not passed to either bootstrap runner; those build paths using the monthly default. `--enhanced-sensitivities` likewise bypasses `--fixed-block-length` rather than rejecting an incompatible combination.
3. **Expected behavior:** a run should either propagate the resolved rebalancing/resampling design consistently or reject unsupported combinations explicitly.
4. **Consequence:** an invocation requesting quarterly inference could silently produce uncertainty for a different estimand; an enhanced fixed-block invocation could silently produce stationary draws.
5. **Existing outputs affected:** none of the reported intervals. Quarterly results are point estimates only, and the published fixed-block runs use the ordinary runner.
6. **Minimal correction:** thread rebalancing through the bootstrap runners or reject nonmonthly/bootstrap combinations until supported; reject unsupported enhanced/fixed-block combinations.
7. **Recomputation:** only hypothetical affected runs, not any current publication result.

### Minor m4: resume does not verify run identity

1. **Locations:** `study.py:99`--`:115`; `study.py:_run_manifest` at `:41`--`:55`.
2. **Observed behavior:** resume reads the existing draws, takes the largest replication ID, and appends a newly requested chunk. It does not verify the original seed, data, cost, lookback, horizon, displacement, gamma, bootstrap scheme, or versions. Original point-estimate files are rewritten before any such comparison.
3. **Expected behavior:** resume should require the same resolved scientific specification and frozen inputs and validate contiguous completed IDs before writing.
4. **Consequence:** changing a CLI/config option between chunks could create a mixed bootstrap distribution with internally misleading point estimates.
5. **Existing outputs affected:** no evidence of mixed published runs. All five final registries have the correct complete ID ranges and fixed block lengths; first-replication reconstructions and the final enhanced-replication reconstruction are recorded in the evidence.
6. **Minimal correction:** record and compare the complete resolved specification/input identity before appending or overwriting; fail explicitly on differences.
7. **Recomputation:** none indicated for the current outputs. Only a run proven to contain mixed settings would require rebuilding.

### Minor m5: input validation does not fully enforce monthly uniqueness/continuity

1. **Locations:** `ingest.py:48`--`:58`; `countries.py:46`--`:49`; `engine.py:35`--`:39`.
2. **Observed behavior:** the industry parser accepts January and March with February absent; the engine then counts adjacent rows as adjacent months. The country parser constructs `dict(records)` before checking duplicate dates, silently keeping the final value for a repeated month.
3. **Expected behavior:** reject missing calendar months and duplicate monthly records before destructive aggregation.
4. **Consequence:** malformed future inputs could shorten rolling windows or overwrite source observations silently.
5. **Existing outputs affected:** none. All three actual processed panels match complete month-end calendars. Independently scanning the broader country raw sections found no duplicated monthly records.
6. **Minimal correction:** validate expected monthly calendars and retain records until duplicate detection has run; add missing-month and duplicate-month parser tests.
7. **Recomputation:** none for the frozen data.

### Minor m6: the written LW formula leaves its covariance divisor ambiguous

1. **Locations:** `methods.py:29`, `:75`; submitted `main.tex:63`--`:75` (the sample-GMV and LW definitions).
2. **Observed behavior:** sample GMV uses sample covariance with divisor L-1. `sklearn.covariance.LedoitWolf` uses a centered empirical covariance with divisor L. The manuscript uses the same symbol S in the two expressions. A direct numerical check confirms the library covariance equals the stated shrinkage formula with the **divisor-L** empirical covariance.
3. **Expected behavior:** distinguish the empirical covariance used inside the LW estimator from the unbiased sample covariance used for sample GMV, or state the library convention explicitly.
4. **Consequence:** an independent reimplementation could use a different normalization. Common positive covariance scaling leaves exact GMV weights unchanged; the issue is definition clarity, not an identified change in the paper's conclusions.
5. **Existing outputs affected:** no numerical correction is indicated; the code implements the standard library estimator and reproduces the saved outputs.
6. **Minimal correction:** clarify the covariance convention in implementation notes. Retain the frozen code convention.
7. **Recomputation:** none.

### Minor m7: nonexistent appendix sub-section reference

1. **Location:** submitted `main.tex:85`.
2. **Observed behavior:** the main text cites Appendix Sections F.1--F.2, but `online_appendix.tex` has only Section F and Table A6, without F.1 or F.2.
3. **Expected behavior:** reference Section F and Table A6, or provide the stated subdivisions.
4. **Consequence:** readers cannot follow that particular implementation reference.
5. **Existing outputs affected:** editorial reference only.
6. **Minimal correction:** change the cross-reference to the existing section/table.
7. **Recomputation:** none.

## Explicitly clean scientific areas

| Area | Audit conclusion and evidence |
|---|---|
| Data construction | Raw percent returns are divided by 100, and processed values match raw values to at most about 1.1e-16. Industry panels are 1,201 monthly observations from 1926-07 through 2026-07; countries are 612 from 1975-01 through 2025-12. Asset ordering matches source parsing. No missing or nonfinite observation was found. |
| Country selection | The parser selects the broader `Value-Weight Dollar Returns / All 4 Data Items Not Reqd` section and its first numeric Mkt column, not characteristic portfolios or local-currency returns. The exact uninterrupted-from-January-1975 rule yields the stated 14-country balanced panel. |
| Timing/look-ahead | Formation history ends at t; held returns come from t+1. A synthetic future-return perturbation leaves all weights determined before the perturbation unchanged. OOS starts are 1931-07 for both industry universes and 1980-01 for countries. No look-ahead found in the audited code paths. |
| Allocation methods | EW is 1/N; GMV has nonnegative bounds and a sum-to-one equality; LW uses the scaled-identity library shrinkage covariance; inverse volatility uses ddof=1 standard deviations; ERC uses the convex log-barrier formulation and checks equal contributions. Invalid optimizer status raises rather than substituting a fallback allocation. |
| Numerical feasibility | All baseline held weights are nonnegative and fully invested within floating-point precision. GMV objective tolerance is 1e-10, feasibility tolerance 1e-8, and maximum iterations 2,000. ERC relative budget tolerance is 1e-6, objective tolerance 1e-15, and maximum iterations 2,000. Independent diagonal-GMV and ERC examples agree with their known objectives. |
| State/turnover/cost | Drift is w_i(1+r_i)/(1+r_p). Turnover is half the L1 distance to the pre-trade drifted holdings, and net return is (1-c TO)(1+r_g)-1. Independent month-by-month recomputation matches turnover and net returns for every baseline candidate and ensemble. Initial formation has zero entry cost; no endpoint boundary restarts or double-charges occur. Quarterly off-schedule months drift without trading. |
| CEQ/winners | Annualized CEQ is 12 times mean minus 6 gamma times ddof=1 monthly variance; gamma=5 baseline. CEQ bp multiply annualized decimals by 10,000. Winners use strict score ordering and deterministic exact-tie priority, without a tie tolerance. |
| Endpoint estimand | Original and displaced H=120 windows are sliced from continuous paths; loss is displaced maximum minus the original winner's displaced CEQ. Retained-maximizer losses are zero; losses and regret are nonnegative. Annual dates and h=6/12/24 eligibility match the manuscript. Materiality uses strictly greater than 0.0025. |
| Survival | Monthly first literal/material failure follows the fixed initial method, without resetting after recovery. Administrative censoring and KM risk sets are correct. Complete-follow-up proportions exclude dates without enough available months; KM uses the full eligible annual-origin cohort. Both survival implementations agree on the frozen results. |
| Ex ante | The preceding window includes December d, and the future window starts the next January. Each contains 120 months. They are disjoint within a decision; adjacent annual future windows overlap by 108 months. Selection inherits the chosen candidate's continuously generated net returns and own drifted holdings; no common initialization or transition cost is imposed. The ensemble averages target weights and has its own state, turnover, and costs. |
| Near-tie/conditional diagnostics | Initial, not displaced, CEQs determine the margin. The pairwise probability uses the strict comparison M_switch < M_nonswitch; exact cross-group ties are zero in both universes. The 25-bp split and all method-conditioned counts reproduce. Mean losses are suppressed for n<5; empty equal-weight country cells are not treated as estimated zero outcomes. |
| Bootstrap mechanics | Entire monthly cross-sections share one resampling index, preserving contemporaneous dependence. Stationary continuation wraps circularly and restarts with probability 1/ell. Fixed blocks use circular consecutive blocks and truncate the last block. Each replication rebuilds methods, drift, turnover, costs, CEQs, winners, endpoints, survival, and selectors. Sensitivity cells share the same pseudo-history, and only parameters that affect valuation are repriced from that draw's reconstructed paths. |
| Bootstrap inference | Draws total 2,000 primary plus 1,000 each for country, 30-industry, circular-12, and circular-24. Seeds use SeedSequence([20260909, replication]), so chunks preserve stream identity. Every stored/reported CI is the 2.5th and 97.5th quantile of the relevant saved column. |
| NaNs | Non-reached survival medians appear as NaN in some country and H=180 bootstrap replications. This is an undefined median, not a missing return or a discarded endpoint. None of the reported interval columns contains nonfinite values. The percentile routine rejects nonfinite samples rather than silently dropping them. |
| Final figures | Submitted figure PDFs match the current local figures in extracted text and vector drawing content. The regenerated curves, shares, transition-cell values, omissions, ordering, and labels agree with their sources. Heatmap sparse rows retain their n labels and 0--100 common scale. No confidence graphics are presented for descriptive figures. |

## Publication-to-computation mapping

The complete machine-readable mapping is [artifact_mapping.csv](artifact_mapping.csv). Paths below are relative to `results/` unless stated otherwise.

| Submitted artifact | Scientific computation | Frozen source output | Exact final exporter? |
|---|---|---|---|
| Table 1 | `analysis.endpoint_reproducibility`, switch-conditioned reductions, bootstrap quantiles | Both final `endpoint_pairs.csv` and `outer_bootstrap.csv` | No: exporter lacks final conditional/material rows |
| Table 2 | `analysis.ex_ante_selection`, bootstrap quantiles | Both final `ex_ante_selection.csv` and draw files | Numerical quantities yes; final formatting differs |
| Figure 1 | `diagnostics.survival_audit_from_winners`, `analysis.kaplan_meier`, `frl_publication.main` | Primary literal/material audits in `diagnostics/`; country audits in `extension/` | Yes |
| Figure 2 | `extension._displacement`, `frl_publication.main` | `extension/{primary17,countries}_displacement.csv`, common-origin rows | Yes, with premature rounding issue |
| A1 | Sensitivity path runs; `extension.main`; `diagnostics.audit_summary` | L36/L120/quarterly summaries, gamma/cost CSV, materiality CSV | Same quantities; different baseline rows/layout |
| A2 | `extension._displacement`; 30-industry endpoint/KM/bootstrap reductions | Displacement CSVs and `replication_30_B1000/` | Partial: final two-row granularity panel absent |
| A3 | `near_tie._describe_universe`, `_pairwise_probability`, `extension._margin` | `near_tie_diagnostic/` plus both margin-group CSVs | No final LaTeX emitter |
| A4 | `extension._conditional` | Both `winner_conditioned.csv` files | Emitted as A3; empty-group count differs |
| Figure A1 | `extension._transition`, `frl_publication.main` | Transition counts/row-percent files and winner-conditioned counts | Yes |
| Figure A2 | `extension._loo`, `engine` path building, `frl_publication.main` | Both leave-one-out CSVs and full-universe endpoint means | Yes |
| A5 | `bootstrap` runners/quantiles; `country_bootstrap_report.main` | Five final draw files and country-bootstrap summary CSV | Emitted as A4; final panel order differs |
| A6 | `methods`, `engine`, data parsers, endpoint/selector eligibility | Actual panels, final endpoint and selection files | Emitted as A5; data rows are hard-coded |

## Independently reproduced publication numbers

The exhaustive computed-number ledger is [independently_reproduced_numbers.csv](independently_reproduced_numbers.csv). Row-by-row displayed numerical comparisons for Tables 1--2 and A1--A5 are in [publication_cell_checks.json](publication_cell_checks.json): **62 numerical rows, 267 numerical values**, with the single 12.1% versus 12.0% discrepancy described above. These counts include numerical design labels such as horizons and thresholds, not only estimated statistics. Dataset dates, OOS starts, asset counts, endpoint counts, and decision counts in A6 were independently checked against parsed inputs and rebuilt histories. Portfolio definitions and exact-tie ordering were checked against implementation.

### Main-text and headline tables

| Quantity | 17 industries | 14 countries |
|---|---:|---:|
| Endpoint pairs | 84 | 36 |
| Literal winner changes | 18; 21.4% | 6; 16.7% |
| Loss >25 bp | 5; 6.0% | 4; 11.1% |
| Mean endpoint loss, bp | 7.35 | 10.55 |
| 95% stationary interval, bp | [4.04, 19.60] | [2.14, 21.42] |
| Mean loss conditional on switch, bp | 34.30 | 63.31 |
| Median loss conditional on switch, bp | 8.86 | 71.46 |
| Material share conditional on switch | 27.8% | 66.7% |
| Literal/material median survival, months | 31 / 77 | 40 / 64 |
| Ex ante decisions | 75 | 27 |
| Correct selection rate | 38.7% | 25.9% |
| Mean regret, bp | 109.12 | 48.25 |
| Regret interval, bp | [41.41, 227.02] | [16.91, 221.82] |
| Selector minus ensemble, bp | -10.93 | +58.11 |
| Selector minus ensemble interval, bp | [-75.42, 186.92] | [-108.44, 80.31] |
| Initial-margin medians: switch / nonswitch, bp | 7.42 / 21.50 | 26.57 / 40.65 |
| Strict pairwise smaller-margin proportion | 71.5% (0.714646...) | 65.0% |
| Exact cross-group margin ties | 0 | 0 |
| Switch rate for margin <=25 / >25 bp | 28.3% (15/53) / 9.7% (3/31) | 20.0% (2/10) / 15.4% (4/26) |

### Appendix A1: specification-specific samples

| Setting | Mean loss, bp | Winner change | Literal KM median, months | Endpoint n | Full KM n |
|---|---:|---:|---:|---:|---:|
| Baseline | 7.35 | 21.4% | 31 | 84 | 85 |
| L=36 | 9.17 | 24.4% | 14 | 86 | 87 |
| L=120 | 10.44 | 24.1% | 13 | 79 | 80 |
| Quarterly | 9.28 | 21.4% | 18 | 84 | 85 |
| gamma=2 | 10.99 | 31.0% | 17 | 84 | 85 |
| gamma=10 | 8.10 | 20.2% | 33 | 84 | 85 |
| Cost=0 | 8.20 | 22.6% | 31 | 84 | 85 |
| Cost=50 bp | 8.98 | 20.2% | 26 | 84 | 85 |

On the shared **80 December origins, 1946-12 through 2025-12**, the baseline/L36/L120/quarterly medians are **26/14/13/17**. These are different populations from A1 and are not incorrectly substituted into the final manuscript. Each common-origin cohort has 79 complete 12-month and 78 complete 24-month follow-ups.

| Universe | Failure threshold, bp | Complete S(12) | Complete S(24) | KM median, months |
|---|---:|---:|---:|---:|
| 17 | 0 | 66.7% | 54.2% | 31 |
| 17 | 25 | 89.3% | 79.5% | 77 |
| 17 | 50 | 92.9% | 86.7% | 94 |
| 14 | 0 | 69.4% | 57.1% | 40 |
| 14 | 25 | 77.8% | 68.6% | 64 |
| 14 | 50 | 88.9% | 80.0% | 75 |

The complete-follow-up denominators are 84/83 for the primary 12/24-month rows and 36/35 for countries. Full KM cohorts are 85 and 37, respectively.

### Appendix A2 and Figure 2: common terminal dates

| Universe | h | n | Literal change | Material loss | Mean loss, bp | P90, bp |
|---|---:|---:|---:|---:|---:|---:|
| 17 | 6 | 83 | 13.3% | 4.8% | 3.68 | 4.44 |
| 17 | 12 | 83 | 20.5% | 4.8% | 6.56 | 8.34 |
| 17 | 24 | 83 | 28.9% | **12.0%** | 15.31 | 49.11 |
| 14 | 6 | 35 | 8.6% | 5.7% | 1.77 | 0.00 |
| 14 | 12 | 35 | 17.1% | 11.4% | 10.85 | 26.38 |
| 14 | 24 | 35 | 22.9% | 17.1% | 17.75 | 43.22 |

The 30-industry granularity values reproduce: **11.01 bp [4.97,20.87]**, **38.1%** literal winner changes, and **11 months** median literal survival. Its endpoint and ex ante counts are 84 and 75.

### Appendix A4 and Figure A1: method-conditioned outcomes

All reported initial-winner counts, switch fractions, material-event fractions, and unsuppressed mean losses were reconstructed from independent endpoint CEQs. Primary origin counts in fixed method order are **8,6,55,12,3**; country counts are **0,22,12,1,1**. The empty country EW row is correctly distinguished from a nonempty zero-event row. Transition matrices reproduce all cell percentages and counts; n=1 country rows are descriptive, as the manuscript states.

### Appendix A5: uncertainty

Endpoint-loss stationary/circular intervals reproduce: primary **[4.04,19.60]**, circular-12 **[3.65,18.14]**, circular-24 **[3.87,19.26]**, countries **[2.14,21.42]** bp. Primary full-eligible h=6/12/24 loss estimates/intervals reproduce: **3.59 [1.54,10.91]**, **7.35 [4.04,19.60]**, **15.31 [9.00,40.23]** bp. Their full-eligible denominators are **85,84,83**, not the common n=83 used in A2/Figure 2.

Country secondary rows reproduce: literal switching **16.7% [11.1%,50.0%]**; literal KM S(12) **69.4% [30.6%,80.6%]**; literal KM S(24) **57.9% [13.9%,71.9%]**; hit rate **25.9% [0.0%,59.3%]**; regret and signed selector--ensemble estimates/intervals as above. The country KM S(24) value **57.9%** differs correctly from the complete-follow-up **57.1%** in A1.

## Numbers or claims not independently reproduced

- **12.1%** as the correctly rounded 24-month U.S. material-loss rate: not reproduced; the correct one-decimal value is **12.0%**.
- **Every individual bootstrap replication from raw returns:** not attempted. The full saved distributions and every reported percentile interval were checked; five first draws and the enhanced last draw were regenerated.
- **Exact final LaTeX emission through a repository command:** not available, for the reasons in M1. Numerical reconstruction is successful independently of this missing exporter.
- **Clean checkout acquiring the frozen inputs and generating the final package:** not completed, because the release acquisition/recipe is incomplete and the default country ingestion path fails.
- **A proof of bootstrap coverage for nonsmooth CEQ winner operations:** outside an implementation audit; the manuscript already describes the intervals cautiously.

No remaining reported headline point estimate or interval was found to disagree with its canonical source computation.

## Test coverage and the five highest-risk areas

Existing tests provide useful protection for CEQ annualization/ddof, retained-original-winner endpoint loss, censoring, first-failure no-reset logic, drift/turnover, initial entry-cost treatment, off-schedule quarterly trading, paired selector comparisons, stationary resampling dates/seeds, and fixed-block index range. They are not merely file-existence tests.

Gaps worth targeted tests: PW no-detection fallback; dispatch to the country parser; missing and duplicate calendar months; quarterly/bootstrap argument consistency; resume specification identity; direct exact-tie/zero-loss-switch behavior; direct ex ante window boundary and own-ensemble-cost checks; and the single-rounding percentage example above. These protect concrete failure modes. No production tests or implementation code were changed in the first pass.

| Rank | Scientific code | Why it is high risk | Audit result |
|---|---|---|---|
| 1 | `engine.py:31`--`:87`, continuous paths and ensemble | Timing, drift, turnover, costs, and any reset propagate to every estimand | Clean for published specifications; all baseline states reconstructed |
| 2 | `bootstrap.py:25`--`:247`, selection and full-procedure resampling | Wrong block law, cached original values, or seed identity can invalidate intervals | Published draws/intervals clean; latent fallback and CLI-consistency issues found |
| 3 | `analysis.py:45`--`:85` and `:179`--`:212`, endpoint and ex ante slicing | One-month indexing or winner reuse changes counts, loss, and regret | Independent array reconstruction agrees for all three universes |
| 4 | `diagnostics.py:70`--`:170`, first failure and survival populations | Reset/censoring/cohort differences can alter median and S(h) interpretation | Clean; specification/common-cohort and KM/complete distinctions verified |
| 5 | `methods.py:47`--`:112`, covariance optimization | Solver status, normalization, or constraints can alter close winners | Published calculations reproduce; library covariance divisor should be explicit |

## Judgment on the reproducibility claims

The repository supports the manuscript's scientific calculations **with the existing frozen local inputs and saved bootstrap distributions**. The checks found no look-ahead, turnover/cost accounting defect, endpoint/selector-window error, survival-reset defect, or numerical mismatch affecting a reported scientific conclusion. One minor displayed percentage should be corrected.

It does **not yet support the stronger claim that the exact final manuscript and appendix can be regenerated from a clean checkout using the documented commands**. Completing the final exporter and frozen replication release should resolve that gap without a new scientific analysis or full bootstrap rerun. The latent code defects should be fixed with the targeted tests identified above before using the repository for additional specifications.

## Completion note

All first-pass computational checks completed successfully. The **31/31** omitted-asset reconstructions match all five saved fields per omission. The **five** replication-0 reconstructions match their saved bootstrap statistics; the enhanced primary final replication **1999** matches **all 223 fields**, including baseline, h/H/gamma/cost cells and paired differences, with maximum finite absolute discrepancy 4.44e-16. All **40** saved two-sided interval definitions across the five runs reproduce, together with the three primary displacement intervals. All three baseline endpoint and ex ante tables, and the lookback/quarterly endpoint tables, match independently calculated CEQs to floating-point precision. The existing **22** tests pass.

Among the **267** numerical tokens checked in the submitted Tables 1--2 and A1--A5, the sole mismatch is the rounding issue in A2. It is repeated in the Results prose. Table A6's dates/counts/definitions have also been checked. This completion does not imply that the full 6,000 bootstrap histories were rerun; the audit limits stated at the beginning still apply.

Leave-one-out mean endpoint losses remain positive for every omission: **6.71--10.61 bp** for industries and **5.37--15.19 bp** for countries. The corresponding influence ranges are **-0.64 to +3.26 bp** and **-5.18 to +4.64 bp**. These verify the artwork and describe influence; they are not inferential or causal estimates.

Production source, configurations, final manuscript source, and frozen empirical/publication files were preserved. The Git tracked-file diff remains empty. Audit outputs and standalone verification scripts are available only under `results/scientific_audit/`.
