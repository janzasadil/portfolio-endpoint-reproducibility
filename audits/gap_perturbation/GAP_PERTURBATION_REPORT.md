# Gap-perturbation and durability diagnostic

Descriptive exploratory accounting only; no inference or manuscript changes.

## Identity and tie audit

The identity passed for all 3,659 pair/cohort records (including explicitly labeled common-origin copies). Maximum absolute residual: 3.4694469519536142e-17 native annualized CEQ (3.4694469519536142e-13 bp). Method-level maximum residual: 4.163336342344337e-17. Validation tolerance is 1e-12; it never changes winner selection, positive-loss classification, or threshold comparisons.

| Baseline universe (H=120, h=12) | Pairs | Reported changes | Positive losses | Mismatches |
|---|---:|---:|---:|---:|
| 17 U.S. industries | 84 | 18 | 18 | 0 |
| 14 developed-country markets | 36 | 6 | 6 | 0 |
| 30 U.S. industries | 84 | 32 | 32 | 0 |

Across all covered cohorts: 0 classification mismatches; 0 reported changes with zero stored loss. Every mismatch, its cause, all initial/shifted CEQs, and exact/apparent top-tie methods are in `winner_change_tie_audit.csv`.

Exact shifted top ties: 0; apparent shifted top ties within 1e-12 CEQ: 0. Minimum absolute shifted separation among any two candidate CEQs: 3.3005393425267204e-08; minimum strictly positive separation: 3.3005393425267204e-08. Minimum best/runner-up separation: 4.9108986277524025e-07. These are native CEQ units, not bp.

Minimum best/runner-up separation around an apparent top tie: not applicable: no apparent top ties at the stated tolerance.

Initial endpoint exact/apparent top ties: 0/0. Minimum absolute separation across either endpoint: 3.3005393425267204e-08. Candidate-pair apparent ties (including below the top): 0. Their methods, CEQs, and separations are in `apparent_ceq_tie_audit.csv`.
Stored positive loss agrees with direct shifted-window nonattainment of the maximum for every record: True.

Winner ties do not affect the covered empirical classifications.

## Gap and relative perturbation pattern

The competitor is the maximizer of the computed delta-minus-gap vector under the frozen method ordering. The initial winner is included: on unchanged-winner observations it usually maximizes with gap=delta=excess=0. All-pair summaries therefore contain structural zeros. The decomposition is an exact accounting identity, not a causal explanation.

| Universe | Conditioning | n | Mean gap (bp) | Mean relative perturbation (bp) | Mean excess (bp) |
|---|---|---:|---:|---:|---:|
| 17 U.S. industries | all_pairs | 84 | 7.67 | 15.02 | 7.35 |
| 17 U.S. industries | reported_winner_change | 18 | 35.77 | 70.07 | 34.30 |
| 17 U.S. industries | endpoint_loss_gt25bp | 5 | 85.91 | 189.62 | 103.71 |
| 14 developed-country markets | all_pairs | 36 | 10.52 | 21.07 | 10.55 |
| 14 developed-country markets | reported_winner_change | 6 | 63.13 | 126.44 | 63.31 |
| 14 developed-country markets | endpoint_loss_gt25bp | 4 | 76.70 | 168.37 | 91.67 |
| 30 U.S. industries | all_pairs | 84 | 13.34 | 24.35 | 11.01 |
| 30 U.S. industries | reported_winner_change | 32 | 35.03 | 63.93 | 28.90 |
| 30 U.S. industries | endpoint_loss_gt25bp | 12 | 77.16 | 139.31 | 62.15 |

Median, p75, and p90 for each quantity and every separately labeled cohort are in `gap_perturbation_summary.csv`. Phase samples, H=60 checks, full eligible samples, and common-origin copies must not be pooled as independent observations.

17 U.S. industries: among reported switches the median initial competitor gap is 8.79 bp, median relative perturbation 22.93 bp, and median excess 8.86 bp. In the >25-bp subset, the mean initial gap is 85.91 bp versus 35.77 bp among all switches. These descriptively larger gaps require correspondingly larger relative perturbations; material failures are not simply the smallest initial races. Sparse conditional groups warrant caution.
14 developed-country markets: among reported switches the median initial competitor gap is 50.23 bp, median relative perturbation 158.87 bp, and median excess 71.46 bp. In the >25-bp subset, the mean initial gap is 76.70 bp versus 63.13 bp among all switches. These descriptively larger gaps require correspondingly larger relative perturbations; material failures are not simply the smallest initial races. Sparse conditional groups warrant caution.
30 U.S. industries: among reported switches the median initial competitor gap is 12.37 bp, median relative perturbation 24.55 bp, and median excess 15.22 bp. In the >25-bp subset, the mean initial gap is 77.16 bp versus 35.03 bp among all switches. These descriptively larger gaps require correspondingly larger relative perturbations; material failures are not simply the smallest initial races. Sparse conditional groups warrant caution.

## Durability surface

Direct proportions use December origins with at least h observed future months. For each origin the initial winner is held fixed; losses are calculated from saved monthly CEQs and accumulated with a running maximum over months 1 through h. A first loss strictly greater than tau is permanent failure, even after recovery. Grid: h=1..120, tau=0..100 CEQ bp in 1-bp steps. No Kaplan--Meier censoring adjustment is used. Denominators N_h change with h; horizon profiles need not be monotone because cohorts change. For fixed h they must be nondecreasing in tau. Tau=0 measures continued attainment of the CEQ maximum, not necessarily unchanged reported identity in a tie.

All twelve 0/25/50-bp slices at h=12/24 reproduce the existing complete-follow-up estimates and eligible counts. They are not mislabeled as the existing full-sample KM estimates.

| Universe | h | N_h | S(h,0) | S(h,25) | S(h,50) | S(h,100) |
|---|---:|---:|---:|---:|---:|---:|
| 17 U.S. industries | 12 | 84 | 66.7% | 89.3% | 92.9% | 95.2% |
| 17 U.S. industries | 24 | 83 | 54.2% | 79.5% | 86.7% | 89.2% |
| 17 U.S. industries | 60 | 80 | 37.5% | 62.5% | 68.8% | 71.2% |
| 17 U.S. industries | 120 | 75 | 30.7% | 40.0% | 44.0% | 45.3% |
| 14 developed-country markets | 12 | 36 | 69.4% | 77.8% | 88.9% | 91.7% |
| 14 developed-country markets | 24 | 35 | 57.1% | 68.6% | 80.0% | 88.6% |
| 14 developed-country markets | 60 | 32 | 34.4% | 46.9% | 59.4% | 78.1% |
| 14 developed-country markets | 120 | 27 | 3.7% | 11.1% | 22.2% | 51.9% |

At h=120, increasing tolerance from 50 to 100 bp raises persistence by 1.3 percentage points for 17 U.S. industries. This quantifies the extra threshold detail beyond the existing 0/25/50-bp slices.

At h=120, increasing tolerance from 50 to 100 bp raises persistence by 29.6 percentage points for 14 developed-country markets. This quantifies the extra threshold detail beyond the existing 0/25/50-bp slices.

The surface exposes intermediate tolerance thresholds and horizons, but the rows above largely extend the already reported literal/material persistence contrast. It is a useful inspection artifact, not a new estimand or inferential result. A changing-cohort heatmap is less direct for the paper than its existing 0/25/50-bp survival presentation.

## Recommendation

**Decomposition only.** Use the gap/perturbation accounting as a compact descriptive diagnostic; keep the full durability surface in the reproducibility package. It adds threshold detail but is substantially redundant with existing persistence results and uses a different complete-follow-up population from the KM curves. No automatic manuscript insertion is recommended.

## Reused versus recomputed

- Reused canonical baseline endpoint-pair CEQs, losses, and winners for all three universes.
- Reused existing H=120/H=60 monthly endpoint-pair CEQs for all twelve annual calendar phases of the primary and country universes.
- Recovered complete H=120 monthly CEQ panels by merging persisted earlier/later scores; overlapping copies agree exactly.
- Reconstructed h=6/24 December pairs by looking up saved monthly CEQs; validated the existing full/common-origin profiles.
- Computed algebraic gaps, relative perturbations, residuals, tie audits, and descriptive summaries from those saved CEQs.
- Computed running maxima and complete-follow-up surface proportions from those same monthly CEQs; checked existing 0/25/50-bp slices.
- No CEQs, portfolio paths, bootstrap replications, manuscript files, or publication outputs were recomputed or modified.

30-industry coverage is the saved baseline H=120/h=12 CEQ pairs only. Its monthly CEQs and h=6/24 CEQ pairs were not persisted here, so no paths were rebuilt to extend that scope.

Input paths, grids, tolerance, and exact coverage are recorded in `diagnostic_manifest.json`.
