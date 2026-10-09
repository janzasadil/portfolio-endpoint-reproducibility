# Frozen paper replication package

Restore the companion archive into an empty directory, then use Python 3.13.3:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-frozen.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m pytest -q
python scripts/reproduce_publication.py
```

The single command verifies the 54 frozen inputs, recomputes A6/A7 from saved monthly CEQs and continuous net paths, and generates Tables 1, 2, A1-A7 and Figures 1, 2, A1, A2 in `results/reproduced_publication/`. It checks all nine LaTeX files byte for byte against `generated/`, the seven core bodies against the archived reference, and all printed core values against the submitted source. It adds native A6/A7 inputs to the supplement.

No download, portfolio reconstruction or bootstrap runs. Use a fresh `--output-dir` to repeat. The optional `--gap-scatter` renders an additional diagnostic without inserting it into the paper. PDFs are visual outputs, not table sources. The supplied journal class has a known current-LaTeX compatibility issue documented in QF_V4_PUBLICATION.md.

The code-only repository lacks the companion inputs and external journal ZIP; tests use small committed fixtures. MIT applies to code, not French datasets or journal files. Read QF_RELEASE_STATUS.md before a public deposit. No DOI or public companion download is claimed.

Historical executed bootstrap counts are preserved in `replication/frozen_run_registry.json`: primary stationary B=2000; country, 30-industry and each fixed-block sensitivity B=1000. Protocol configuration is not a claim of completed replication counts.
