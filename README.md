# Portfolio Endpoint Reproducibility

Code for *Reproducibility of portfolio method comparisons: Terminal-date sensitivity and endpoint loss* by Jan Zasadil. The paper asks how a change in the evaluation endpoint affects the initial portfolio-method winner and its CEQ loss.

The frozen design uses 17 U.S. industries, 14 developed-country USD market portfolios and a 30-industry robustness sample; a 60-month estimation window, 120-month evaluation window, monthly rebalancing, transaction costs of 25 bp per unit of turnover and risk aversion gamma=5. The main displacement is 12 months and the material-loss threshold is 25 annualized CEQ bp.

## Reproduce the paper

Use Python **3.13.3** (`.python-version`) and the pinned numerical environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-frozen.txt
python -m pip install --no-deps --no-build-isolation -e .
python scripts/reproduce_publication.py
```

**Required companion inputs:** restore the frozen paper archive into this checkout first. It must supply the 54 files in `replication/qf_input_manifest.json` and `replication/qf_source_template.zip`. The script verifies checksums before generation. The companion archive is currently local; no public download or DOI is available yet. A Git clone alone can run tests and inspect the committed tables, but cannot reconstruct the paper without these inputs. Publishing that companion is the remaining reproducibility gap.

The command writes a fresh `results/reproduced_publication/` containing:

- Tables **1, 2, A1-A7**, generated as native LaTeX with notes and labels;
- Figures **1, 2, A1, A2**, regenerated from saved diagnostics with CSV plotting ledgers;
- Manuscript sources that input the tables, numerical audits and provenance manifests.

It recomputes A6 first-passage/fixed-horizon categories and A7 CEQ components from saved monthly CEQs and continuous net paths. It runs no portfolio optimization or bootstrap. All nine tables must match committed `generated/*.tex` **byte for byte**. Use `--output-dir PATH` for another fresh package; existing publication directories are never overwritten.

The optional `--gap-scatter` regenerates the gap/perturbation diagnostic; it is not automatically inserted or assigned a paper figure number. PDFs are rendering outputs, never the source of table values. The supplied legacy journal class has a documented issue with current LaTeX; see [QF_V4_PUBLICATION.md](QF_V4_PUBLICATION.md) for compilation details.

## Data and environment

Returns come from the Kenneth R. French Data Library. Frozen raw snapshots, parsed panels and completed simulations are outside Git and checksum-recorded. `portfolio-ingest` can download fresh data for new research; do not replace frozen paper inputs. See [data/README.md](data/README.md) and [DATA_MANIFEST.md](DATA_MANIFEST.md) for provenance. The MIT code license does not license French data or third-party journal assets.

`requirements-frozen.txt` pins the recorded numerical/test environment. Broader compatibility bounds in `pyproject.toml` are not the paper environment. Numerical cells and LaTeX bytes are checked; identical PDF bytes across rendering-library versions are not promised.

## Validation

```powershell
python -m pytest -q
python scripts/validate_publication_results.py
```

Tests work from a code-only checkout using small committed supplemental fixtures. The second command requires the reproduced package: it verifies frozen input hashes, the seven core table bodies against their archived reference, printed manuscript values against frozen results, and all nine generated LaTeX files against committed versions. A6/A7 tests cover monthly-event definitions, strict threshold boundaries, CEQ identities, deterministic export and rejection of inconsistent saved inputs.

## Repository map

- `src/portfolio_endpoint/`: scientific analyses, data loading and publication generation.
- `scripts/reproduce_publication.py`: current paper reproduction entry point.
- `generated/`: committed native LaTeX tables for manuscript inputs.
- `tests/`: validation suite and small saved-result fixtures.
- `replication/`: frozen inventories, numerical references and release instructions.
- `exploratory/`: unreported selector/frontier experiments, excluded from paper reproduction and the archive.
- `data/`, `results/`, `output/`, `tmp/`, `release/`: local inputs, generated runs, QA and archive artifacts, generally ignored by Git.

[SCIENTIFIC_CORE.md](SCIENTIFIC_CORE.md) maps the core paper to code; [QF_V4_PUBLICATION.md](QF_V4_PUBLICATION.md) documents table generation. [REPLICATION.md](REPLICATION.md) describes the historical FRL package.

## Citation and license

Use [CITATION.cff](CITATION.cff) to cite this repository version. A paper/deposit DOI will be added after publication. Code uses the [MIT License](LICENSE); third-party data and journal assets retain their own terms. [replication/QF_RELEASE_STATUS.md](replication/QF_RELEASE_STATUS.md) records the remaining public-archive steps.
