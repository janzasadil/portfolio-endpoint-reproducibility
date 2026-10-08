# Export validation

- Seven generated tables, 15 numerical bodies, 342 printed numerical tokens:
  zero differences from the supplied V4 source.
- Full test suite: 63 passed. Dependency deprecation warnings only.
- All seven tables compiled in a standalone PDF preview; seven pages inspected,
  with no clipping, overlapping cells or undefined references. The second-pass
  log contains no LaTeX warnings or overfull boxes.
- Full journal manuscript compilation is **not verified locally**. The supplied
  2018 kernel rollback and journal class fail with the installed TeX Live 2025
  packages before the tables (`\veqno` at the first numbered equation). A temporary
  test without rollback also fails (`Extra \endgroup`). Exported preambles and
  journal class are unchanged. Use the compatible environment that produced the
  supplied final PDF, or make a separate journal-template compatibility update.
- The standalone preview is a table proof, not a recompiled final manuscript.
- No empirical pipeline or bootstrap was rerun. Figures remain supplied assets.
