# Fixed-method and base-rate benchmark

H=120; the existing annual December decision dates and saved preceding/following-window CEQs are reused without changing holdings, costs, windows, or candidate methods. Shares in the CSVs are native proportions; this report displays percentages. Both benchmark choices use the realized following-window sample and are retrospective descriptive benchmarks, not deployable selectors.

## Table A — Future-best base rates

### 17_industries (D=75)

| Method | Future-best count | Future-best share |
|---|---:|---:|
| Equal weight | 7 | 9.3% |
| Sample GMV | 6 | 8.0% |
| Ledoit–Wolf GMV | 47 | 62.7% |
| Inverse volatility | 11 | 14.7% |
| ERC | 4 | 5.3% |

Preceding-winner hit rate: **38.7%**; majority constant-label rate: **62.7%** (Ledoit–Wolf GMV); difference: **-24.0 percentage points**.

### 14_countries (D=27)

| Method | Future-best count | Future-best share |
|---|---:|---:|
| Equal weight | 0 | 0.0% |
| Sample GMV | 15 | 55.6% |
| Ledoit–Wolf GMV | 11 | 40.7% |
| Inverse volatility | 0 | 0.0% |
| ERC | 1 | 3.7% |

Preceding-winner hit rate: **25.9%**; majority constant-label rate: **55.6%** (Sample GMV); difference: **-29.6 percentage points**.

## Table B — Fixed-method regret

### 17_industries

| Method | Mean regret (CEQ bp) | Median regret (CEQ bp) | Future-best share |
|---|---:|---:|---:|
| Equal weight | 210.11 | 192.22 | 9.3% |
| Sample GMV | 76.86 | 28.47 | 8.0% |
| Ledoit–Wolf GMV | 46.84 | 0.00 | 62.7% |
| Inverse volatility | 160.58 | 153.89 | 14.7% |
| ERC | 148.31 | 140.67 | 5.3% |

Preceding-winner mean regret: **109.12 bp**; best fixed method: **Ledoit–Wolf GMV**, with mean regret **46.84 bp**; selector minus best fixed: **+62.28 bp**.

Majority label also minimizes mean fixed-method regret: **True**. Future-best exact CEQ ties: **0 dates**. All majority objective ties: ledoit_wolf_gmv; all minimum-regret objective ties: ledoit_wolf_gmv.

### 14_countries

| Method | Mean regret (CEQ bp) | Median regret (CEQ bp) | Future-best share |
|---|---:|---:|---:|
| Equal weight | 239.12 | 259.13 | 0.0% |
| Sample GMV | 21.04 | 0.00 | 55.6% |
| Ledoit–Wolf GMV | 28.11 | 13.94 | 40.7% |
| Inverse volatility | 207.82 | 213.03 | 0.0% |
| ERC | 204.41 | 230.50 | 3.7% |

Preceding-winner mean regret: **48.25 bp**; best fixed method: **Sample GMV**, with mean regret **21.04 bp**; selector minus best fixed: **+27.21 bp**.

Majority label also minimizes mean fixed-method regret: **True**. Future-best exact CEQ ties: **0 dates**. All majority objective ties: sample_gmv; all minimum-regret objective ties: sample_gmv.

## Validation and interpretation

Both decision counts and all four requested headline values reproduced. Unrounded hit rates and regrets match the frozen summaries within 1e-12 native CEQ/proportion units. Every saved selected method, future-best label, selector hit, and regret is checked against the persisted CEQs using the existing exact deterministic method ordering. Exact future-best ties count as one reported label, not multiple hits; tie details are in the tie-audit CSV.

17_industries: the preceding-window winner's hit rate is below the retrospectively chosen majority base rate, and its mean regret is higher than the retrospectively chosen best fixed method's regret.
14_countries: the preceding-window winner's hit rate is below the retrospectively chosen majority base rate, and its mean regret is higher than the retrospectively chosen best fixed method's regret.

On these two descriptive criteria, the preceding-window winner offers no performance advantage over the hindsight-selected fixed-method benchmarks in either sample. This does not prove an absence of prospective information.

These comparisons assess incremental descriptive performance against generally strong methods; they do not establish predictive skill or statistical significance. The benchmark choices use hindsight, and overlapping following windows are not independent. No bootstrap or other expensive computation ran, and existing empirical/publication files were not modified.
