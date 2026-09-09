# Execution manifest

This manifest records the machine-level choices that implement the frozen scientific protocol. It must be completed and committed immediately before the final empirical run; changing it afterward requires an explicitly classified correction or exploratory branch.

## Fixed implementation choices

| Item | Current pinned choice |
| --- | --- |
| GMV solver | SciPy SLSQP; analytic gradient; deterministic equal-weight initialization |
| GMV retry | None; a failed validation invalidates the run |
| ERC solver | SciPy L-BFGS-B on the frozen convex risk-budget objective; deterministic all-ones initialization |
| Feasibility tolerance | `1e-8` |
| Objective tolerance | `1e-10` (GMV); `1e-15` (ERC) |
| Maximum solver iterations | `2000` |
| ERC relative risk-contribution tolerance | `1e-6` |
| Bootstrap | Circular stationary bootstrap with geometric blocks; corrected Politis–White selector |
| Outer / inner replications | `5000` / `2000` |
| Outer RNG seed | `20260909` |

## To record at final execution

- Python, NumPy, pandas, SciPy, and scikit-learn versions;
- SHA-256 of `config/experiment.yaml`, source files, and the exact Git commit;
- exact dataset checksums already recorded in `DATA_MANIFEST.md`;
- selected outer block length for each universe;
- generated result-file checksums and run timestamp.

The 5,000-rep outer run and 2,000-rep endpoint-specific inner runs have not yet been launched.
