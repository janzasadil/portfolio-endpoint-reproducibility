# Post-referee extraction audit

## Sources

- Frozen `endpoint_pairs.csv` and `outer_bootstrap.csv` from the 17-industry, 14-country, and 30-industry final runs.
- Exact processed monthly return histories under `data/processed/` for deterministic block-length reconstruction.
- `portfolio_endpoint.bootstrap.protocol_block_length` and `corrected_pw_stationary_block_length`.

## Design preservation

No scientific specification, universe, threshold, or inference procedure was changed. No bootstrap was rerun. Block lengths were deterministically reconstructed because final manifests do not record component selector values, then confirmed against the fixed block-length column in every saved bootstrap draw.

## Headline-count verification

- 17_industries: 84 pairs; 18 switches (21.4%); 5 losses >25 bp (6.0%).
- 14_countries: 36 pairs; 6 switches (16.7%); 4 losses >25 bp (11.1%).
