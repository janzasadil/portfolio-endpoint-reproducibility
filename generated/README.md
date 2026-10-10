# Generated publication tables

All nine table files are generated native LaTeX. Do not edit them by hand. Regenerate with `python scripts/reproduce_publication.py`; validation checks every table against this committed snapshot.

A manuscript in a neighboring directory can use `\input{../generated/table_1.tex}`, followed by the other main and supplemental table inputs. Reproduced packages use `tables/` for all table inputs. See [reproduction documentation](../docs/REPRODUCIBILITY.md) for the supported packages and optional journal assembly.
