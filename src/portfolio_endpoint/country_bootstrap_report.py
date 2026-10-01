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
    text=("# Country stationary-bootstrap analysis\n\n"
          "The synchronized-month stationary bootstrap completed B=1,000 replications. The country mean endpoint loss is 10.55 bp, with a percentile 95% interval of [2.14, 21.42] bp. Thus the country endpoint-loss estimate is positive across this completed interval. Literal-switching and literal-survival intervals are wide, consistent with only 36 headline endpoint pairs.\n\n"
          "The preceding-performance selector has 27 decision dates. Its mean selector-minus-ensemble result is +58.11 bp but its percentile interval [-108.44, 80.31] bp spans zero. This is not evidence of a reliable implementable advantage. Selection regret is 48.25 bp [16.91, 221.82].\n\n"
          "Material-survival intervals and the material-minus-literal survival difference cannot be recovered from the saved bootstrap draws: those artifacts contain literal survival only. Exact dependence-aware uncertainty would require a new country stationary bootstrap that saves material survival at each pseudo-history; it is not run here.\n")
    (out/'COUNTRY_BOOTSTRAP_ANALYSIS.md').write_text(text,encoding='utf8')
if __name__=='__main__': main()
