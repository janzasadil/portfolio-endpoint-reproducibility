# v1.0.0-paper-submission

This code snapshot provides one reproduction command for Tables 1, 2, A1-A7 and four core figures. A6/A7 are proper analyses of frozen monthly CEQs and continuous net returns. Native LaTeX tables are committed; regeneration validates their exact bytes. MIT licensing, pinned dependencies, Python version, citation metadata and validation commands are included. Unreported experiments are separated under exploratory/ and omitted from the paper archive.

Run `python scripts/reproduce_publication.py` after restoring the frozen companion inputs. Run `python -m pytest -q` on a code-only checkout.

The frozen companion remains local pending third-party redistribution resolution. This source-only release does not by itself supply all inputs for reproducing the numerical paper. No DOI has been assigned.
