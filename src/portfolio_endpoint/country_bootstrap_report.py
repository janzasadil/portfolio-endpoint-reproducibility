"""Summarize the completed country B=1000 stationary bootstrap."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .ingest import project_root

def main() -> None:
    root=project_root(); run=root/'results/country_replication_B1000'; out=root/'results/extension'
    draws=pd.read_csv(run/'outer_bootstrap.csv'); summary=json.loads((run/'summary.json').read_text()); manifest=json.loads((run/'run_manifest.json').read_text())
    if len(draws)!=manifest['outer_bootstrap_replications'] or len(draws)!=1000: raise ValueError('Country bootstrap is incomplete')
    metrics=[('Mean endpoint loss','mean_endpoint_loss','bp'),('Literal switching','literal_switch_frequency','%'),('Censored-KM literal S(12)','survival_12_months','%'),('Censored-KM literal S(24)','survival_24_months','%'),('Selection regret','mean_selection_regret','bp'),('Selector minus ensemble','mean_selector_minus_ensemble','bp'),('Selector hit rate','selector_hit_rate','%')]
    rows=[]
    for label,col,unit in metrics:
        scale=10000 if unit=='bp' else 100
        lo,hi=np.percentile(draws[col],[2.5,97.5])
        rows.append({'metric':label,'point_estimate':summary[col]*scale,'ci_low':lo*scale,'ci_high':hi*scale,'unit':unit,'bootstrap_replications':len(draws)})
    table=pd.DataFrame(rows); table.to_csv(out/'country_bootstrap_B1000_summary.csv',index=False)
    def rendered(label, signed=False):
        row=table.set_index('metric').loc[label]
        point=format(row.point_estimate,'+.2f' if signed else '.2f')
        return f'{point} {row.unit} [{row.ci_low:.2f}, {row.ci_high:.2f}]'
    decisions=len(pd.read_csv(run/'ex_ante_selection.csv'))
    pairs=len(pd.read_csv(run/'endpoint_pairs.csv'))
    text=("# Country stationary-bootstrap analysis\n\n"
          f"The synchronized-month stationary bootstrap completed B={len(draws):,} replications. "
          f"Mean endpoint loss (95% percentile interval): {rendered('Mean endpoint loss')}. "
          f"The headline sample contains {pairs} endpoint pairs.\n\n"
          f"The preceding-performance selector has {decisions} decision dates. "
          f"Selector minus ensemble: {rendered('Selector minus ensemble',signed=True)}. "
          f"Selection regret: {rendered('Selection regret')}. "
          "These are saved-draw uncertainty summaries, not a guarantee of an implementable advantage.\n\n"
          "Material-survival intervals and the material-minus-literal survival difference cannot be recovered from the saved bootstrap draws: those artifacts contain literal survival only. Exact dependence-aware uncertainty would require a new country stationary bootstrap that saves material survival at each pseudo-history; it is not run here.\n")
    (out/'COUNTRY_BOOTSTRAP_ANALYSIS.md').write_text(text,encoding='utf8')
if __name__=='__main__': main()
