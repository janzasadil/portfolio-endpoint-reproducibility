# Frozen paper inputs

Git stores code, metadata, generated LaTeX and small supplemental validation fixtures, not raw/processed market data or completed simulations.
The local QF replication candidate supplies the three exact French ZIP snapshots,
their processed panels, and the saved scientific outputs required by the exporter.
Never replace those files with current downloads when reproducing the paper.

`replication/qf_input_manifest.json` pins all 54 required inputs by checksum.
Country returns are the broader USD value-weighted Mkt series (all four valuation
ratios not required), balanced from January 1975; coverage depends on B/M data.
The U.S. industry panels cover July 1926-July 2026; countries cover January
1975-December 2025. The 17/14/30-asset samples and exact OOS/eligible dates are
generated in Table A5, not inferred from this overview.

Original source: Kenneth R. French Data Library. These research data are not
relicensed by a software license. Redistribution permission must be confirmed
before a public Zenodo deposit; inclusion in a local candidate is not permission.
