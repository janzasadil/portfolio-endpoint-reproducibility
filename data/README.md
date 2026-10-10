# Data

Raw archives and processed market panels are external inputs, not Git files. See [data provenance](../docs/REPRODUCIBILITY.md#data-provenance), [publication inputs](../replication/publication_inputs.json) and the [full empirical inventory](../replication/full_empirical_archive.json).

Run python scripts/reproduce_analysis.py to download raw archives and regenerate all analysis results. New ingestion records per-dataset JSON in ignored data/provenance/. The software license does not relicense third-party datasets. The optional fast saved-result exporter requires the original paper inputs; the full analysis does not.
