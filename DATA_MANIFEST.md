# Data manifest

This file is part of the research record. The ingestion command appends the exact source URL, UTC retrieval time, SHA-256 checksum, and output dimensions for each downloaded archive. Commit this file after accepting a download as the frozen study input.

| Dataset | File | Retrieved (UTC) | SHA-256 | Rows × columns |
| --- | --- | --- | --- | --- |
| 17 industry portfolios | _pending first ingestion_ | — | — | — |
| 30 industry portfolios | _pending first ingestion_ | — | — | — |

## Transformation protocol

1. Download the official ZIP archive named in `config/experiment.yaml` without modifying it.
2. Extract the `Average Value Weighted Returns -- Monthly` section only.
3. Parse `YYYYMM` dates, map them to month-end timestamps, and reject duplicate months, non-monotone months, missing values, and French missing-value codes (`-99.99`, `-999`).
4. Divide reported percent returns by 100 and write a UTF-8 CSV panel with ISO month-end dates.
5. Record checksums for both the archive and the processed panel below.

The current protocol uses the French library's CIZ-based current return files. A future change requires a new manifest entry, rather than overwriting the recorded data.

| primary_17_industry | `17_Industry_Portfolios_CSV.zip` → `ff_17_industry_value_weighted_monthly.csv` | 2026-09-09T13:47:24+00:00 | raw: `d99108d51938a44559a839df39a92ab531bd36bcd61bf7f6ddf8b89b7b8300c1`; processed: `33a3dc25c6ad938495ee553d674bfb963d0252581bd4a48fd2db7c9f00e244b3` | 1201 × 17 |

| replication_30_industry | `30_Industry_Portfolios_CSV.zip` → `ff_30_industry_value_weighted_monthly.csv` | 2026-09-09T13:47:25+00:00 | raw: `965275065e93d289e416566d1b399fb63cef944a3de46a19a413d7adc869b600`; processed: `bef2e1d5bba9e3eba4766d08aa1f68792dd3f8335a0728bbd93a6c0fdc2148cd` | 1201 × 30 |
