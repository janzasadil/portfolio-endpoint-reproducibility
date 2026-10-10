# Portfolio Endpoint Reproducibility

Replication code for **“Reproducibility of Portfolio Method Comparisons: Terminal-Date Sensitivity and Endpoint Loss.”**

The paper studies the reproducibility of portfolio-method comparisons when the terminal date of a completed historical evaluation is shifted while the candidate methods and evaluation design remain fixed. It distinguishes changes in the reported winner from the economic loss associated with retaining the initial winner.

The empirical analysis compares five long-only portfolio rules using U.S. industry portfolios and developed-country market portfolios. Portfolio weights are estimated from rolling historical data and evaluated on continuous out-of-sample return paths including transaction costs.

## Reproduction

The full analysis downloads the three raw French data archives, constructs portfolio paths, reruns the registered bootstrap and sensitivity analyses, and generates the publication tables and figures. No saved analysis results are required. See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

Reproduction was validated with **Python 3.13.3**.

Create and activate a virtual environment, then run:

```bash
python -m pip install -r requirements-frozen.txt
python -m pip install --no-deps --no-build-isolation -e .
python scripts/reproduce_analysis.py
```

This is a substantial computation with 6,000 bootstrap replications. Results appear in `results/full_reproduction/publication/`; interrupted runs can resume with `--resume`. Paper sample dates and seeds are fixed. Revised source data are identified in the output report and can produce different values from the submitted paper.

## Data

Portfolio returns are obtained from the **Kenneth R. French Data Library**. The replication metadata record the exact input files and checksums used for the paper.

## Validation

Run the test suite with:

```bash
python -m pytest -q
```

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## License

Code is released under the MIT License. Source data remain subject to their original terms of use.
