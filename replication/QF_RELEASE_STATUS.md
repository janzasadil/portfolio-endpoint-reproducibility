# Paper release status

The repository version is 1.0.0; code is MIT licensed. Generated Tables 1, 2 and A1-A7 are committed and checked against deterministic reproduction. The frozen input inventory includes the monthly CEQs and continuous net paths needed for A6/A7. Unreported selector/frontier experiments are outside the publication archive.

A local annotated submission tag and companion ZIP identify this code snapshot. A tag alone is not a public data deposit. The companion ZIP contains frozen third-party French data and journal source files; their rights are separate from MIT. The existing raw-data redistribution question remains unresolved, so the local ZIP must not be described as publicly available.

## Remaining external steps

1. Authenticate GitHub CLI (`gh auth login`) and push the commit and submission tag.
2. Create the GitHub release using `replication/RELEASE_NOTES.md`. Publish a companion download only after resolving third-party redistribution, or provide a permitted alternative carrying exact frozen identities.
3. Archive the release on Zenodo, obtain the actual DOI, then update CITATION.cff and the README with that DOI and the companion download URL.

No GitHub release, Zenodo deposit or DOI is claimed until those operations succeed. The source-only GitHub ZIP cannot reproduce the paper without the companion.
