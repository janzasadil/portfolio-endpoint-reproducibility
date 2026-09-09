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
