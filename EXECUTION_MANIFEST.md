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

The preceding entries describe the original planned execution, not the final
completed run registry. The final primary outer bootstrap used 2,000 paired
replications; country, 30-industry, and 12/24-month circular-block runs used
1,000 each. No inner bootstrap was run. Exact post-audit resolved configurations,
frozen input identities and original manifests are supplied in the replication
release's `replication/frozen_run_registry.json`; see `REPLICATION.md`.
