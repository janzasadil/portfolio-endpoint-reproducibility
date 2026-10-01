"""Deterministic country replication and bounded extension diagnostics."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from .analysis import TIE_BREAK_ORDER, endpoint_reproducibility, endpoint_summary, ex_ante_selection
from .bootstrap import _paths_at_cost
from .diagnostics import (monthly_winner_identities, survival_audit_from_winners, audit_summary,
                          selector_fixed_method_summary, displacement_summary)
from .engine import run_headline_paths
from .ingest import project_root

def _load(root, key):
    c=yaml.safe_load((root/'config/experiment.yaml').read_text()); s=c['study']; d=c['datasets'][key]
    r=pd.read_csv(root/'data/processed'/d['processed_file'],index_col='date',parse_dates=True)
    return r,s

def _base(paths,s):
    e=endpoint_reproducibility(paths,s['evaluation_horizon_months'],12,s['ceq_risk_aversion'])
    w=monthly_winner_identities(paths,s['evaluation_horizon_months'],s['ceq_risk_aversion'])
    lit=survival_audit_from_winners(w); mat=survival_audit_from_winners(w,material_threshold=.0025)
    x=ex_ante_selection(paths,s['evaluation_horizon_months'],s['ceq_risk_aversion'])
    return e,w,lit,mat,x

def _conditional(e):
    rows=[]
    for m,g in e.groupby('earlier_winner'):
        rows.append({'original_winner':m,'n_origins':len(g),'switch_frequency':g.literal_switch.mean(),'mean_endpoint_loss':g.endpoint_loss.mean(),'median_endpoint_loss':g.endpoint_loss.median(),'loss_exceeds_25bp':(g.endpoint_loss>.0025).mean()})
    return pd.DataFrame(rows)

def _transition(e):
    counts=pd.crosstab(e.earlier_winner,e.later_winner).reindex(index=TIE_BREAK_ORDER,columns=TIE_BREAK_ORDER,fill_value=0)
    return counts,counts.div(counts.sum(axis=1).replace(0,np.nan),axis=0)

def _margin(e):
    g=e.assign(margin_group=np.where(e.earlier_margin<=.0025,'<=25bp','>25bp'))
    out=g.groupby('margin_group').agg(n=('endpoint_loss','size'),mean_margin=('earlier_margin','mean'),switch_frequency=('literal_switch','mean'),mean_endpoint_loss=('endpoint_loss','mean'),loss_exceeds_25bp=('endpoint_loss',lambda x:(x>.0025).mean())).reset_index()
    return out,g[['earlier_endpoint','earlier_margin','endpoint_loss','literal_switch','margin_group']]

def _displacement(paths,s):
    tabs={h:endpoint_reproducibility(paths,s['evaluation_horizon_months'],h,s['ceq_risk_aversion']) for h in (6,12,24)}
    common=set.intersection(*(set(x.earlier_endpoint) for x in tabs.values())); rows=[]
    for h,t in tabs.items():
        for sample,q in [('full_eligible',t),('common_calendar_origins',t[t.earlier_endpoint.isin(common)])]: rows.append({'h':h,'sample':sample,**displacement_summary(q)})
    return pd.DataFrame(rows)

def _loo(returns,s):
    rows=[]
    for asset in returns.columns:
        paths=run_headline_paths(returns.drop(columns=asset),60,.0025)
        e,w,lit,_,_= _base(paths,s)
        rows.append({'omitted_asset':asset,'n_assets':returns.shape[1]-1,'n_origins':len(e),'mean_endpoint_loss':e.endpoint_loss.mean(),'literal_switch_frequency':e.literal_switch.mean(),'survival_12_complete_followup':audit_summary(lit)['survival_12_complete_followup']})
    return pd.DataFrame(rows)

def _write_universe(root,out,name,key,loo):
    r,s=_load(root,key); p=run_headline_paths(r,60,.0025); e,w,lit,mat,x=_base(p,s)
    e.to_csv(out/f'{name}_endpoint_pairs.csv',index=False); lit.to_csv(out/f'{name}_literal_origin_audit.csv',index=False); mat.to_csv(out/f'{name}_material25_origin_audit.csv',index=False)
    summary={'endpoint':endpoint_summary(e),'literal_survival':audit_summary(lit),'material25_survival':audit_summary(mat),'n_ex_ante_decisions':len(x),'selector':{'hit_rate':float(x.selector_hit.mean()),'mean_regret':float(x.selection_regret.mean()),'mean_selector_minus_ensemble':float(x.selector_minus_ensemble.mean()),'mean_rank':float(x.selector_rank.mean())}}
    (out/f'{name}_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    _conditional(e).to_csv(out/f'{name}_winner_conditioned.csv',index=False); c,pct=_transition(e); c.to_csv(out/f'{name}_transition_counts.csv'); pct.to_csv(out/f'{name}_transition_row_percent.csv'); a,b=_margin(e); a.to_csv(out/f'{name}_margin_groups.csv',index=False); b.to_csv(out/f'{name}_margin_scatter.csv',index=False); _displacement(p,s).to_csv(out/f'{name}_displacement.csv',index=False); selector_fixed_method_summary(x).to_csv(out/f'{name}_selector_fixed.csv',index=False)
    if loo: _loo(r,s).to_csv(out/f'{name}_leave_one_out.csv',index=False)
    return p,e,w

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path); a=ap.parse_args(); root=project_root(); out=a.output_dir or root/'results/extension'; out.mkdir(parents=True,exist_ok=True)
    p17,e17,w17=_write_universe(root,out,'primary17','primary_17_industry',True)
    pc,ec,wc=_write_universe(root,out,'countries','replication_international_countries',True)
    _,s=_load(root,'primary_17_industry'); rows=[]
    for label,paths,gamma in [('gamma2',p17,2),('gamma5',p17,5),('gamma10',p17,10),('cost0',_paths_at_cost(p17,0),5),('cost25',p17,5),('cost50',_paths_at_cost(p17,.005),5)]:
        e=endpoint_reproducibility(paths,120,12,gamma); w=monthly_winner_identities(paths,120,gamma); lit=survival_audit_from_winners(w)
        rows.append({'setting':label,**endpoint_summary(e),'loss_exceeds_25bp_frequency':float((e.endpoint_loss>.0025).mean()),**audit_summary(lit)})
    pd.DataFrame(rows).to_csv(out/'primary17_gamma_cost_sensitivity.csv',index=False)
    rows=[]
    for name,w in [('primary17',w17),('countries',wc)]:
        for bp in (0,25,50): rows.append({'universe':name,'threshold_bp':bp,**audit_summary(survival_audit_from_winners(w,material_threshold=bp/10000))})
    pd.DataFrame(rows).to_csv(out/'materiality_threshold_sensitivity.csv',index=False)
    (out/'README.md').write_text('Deterministic extension outputs only. No country bootstrap was run. 17-industry A--D outputs are post-results exploratory; country A--D outputs were prospectively frozen.\n',encoding='utf8')
    print(out)
if __name__=='__main__': main()
