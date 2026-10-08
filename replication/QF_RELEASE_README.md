# QF V4 frozen replication candidate

This paper-specific package excludes legacy FRL publication machinery and its
near-tie, post-referee and old reporting utilities. Historical audits remain as
clearly labeled provenance. See RELEASE_STATUS.md before any public deposit.

Use Python 3.13.3 and the recorded numerical environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-frozen.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m pytest -q
python scripts/reproduce_qf.py
```

The last command checks archived file/input checksums, regenerates Tables 1, 2
and A1-A5 plus all four figure PDFs, and verifies the table bodies against the
frozen V4 reference and all 342 printed numerical tokens against the submitted
source. Output: `results/reproduced_qf/`. Choose a new `--output-dir` to repeat;
existing output directories are never overwritten.

No data download, portfolio construction, endpoint/robustness recomputation or
bootstrap is performed by this command. Figure CSV ledgers retain full-precision
plotted values. Numerical identity is required; binary-identical PDFs and identical
fonts across systems are not promised. The full journal manuscript has a known
local LaTeX compatibility issue; table/figure reproduction is distinct from
full-manuscript compilation.

Completed bootstrap counts: primary stationary B=2,000; country, 30-industry and
each 12/24-month circular-block sensitivity B=1,000. No inner bootstrap ran.
The B=5,000 / inner B=2,000 fields in `config/experiment.yaml` preserve the
**planned / protocol configuration, not executed bootstrap replication counts**.
The historical resolved run registry is provenance, not an assertion that old
source hashes match this later export code.

See data/README.md, audits/README.md, QF_V4_PUBLICATION.md and SCIENTIFIC_CORE.md.
The companion ZIP is local until deposited; no DOI/public availability is claimed.
