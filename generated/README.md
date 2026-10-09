# Generated publication tables

These nine native LaTeX tables are committed for direct manuscript inputs. Do not edit them by hand. Regenerate with `python scripts/reproduce_publication.py`; all nine files are verified byte for byte against this snapshot. The provenance headers identify generators and sources.

From a manuscript directory beside this folder, use `\input{../generated/table_A6.tex}` and `\input{../generated/table_A7.tex}`. Reproduced journal packages contain the same files under `tables/` and automatically input A6/A7 after A5. Tables require the journal `\tbl` and `tabnote` conventions plus booktabs, tabularx, array and makecell.
