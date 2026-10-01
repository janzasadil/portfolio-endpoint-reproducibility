"""Generate the lean Finance Research Letters publication bundle."""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from .analysis import kaplan_meier
from .ingest import project_root

def bp(x): return round(10000*x,2)
def pct(x): return round(100*x,1)
def tex(df,path,caption,label):
    d=df.copy()
    d.columns=[str(c).replace('%',r'\%').replace('_',r'\_') for c in d.columns]
    for c in d:
        if d[c].dtype=='object': d[c]=d[c].map(lambda v:v.replace('%',r'\%').replace('_',r'\_') if isinstance(v,str) else v)
    path.write_text('\\begin{table}[H]\n\\centering\n\\small\n\\caption{'+caption+'}\n\\label{'+label+'}\n'+d.to_latex(index=False,escape=False,float_format=lambda x:f'{x:.2f}')+'\\end{table}\n',encoding='utf8')
def curve(audit): return kaplan_meier(audit.rename(columns={'survival_duration_months':'time_months'})[['time_months','event']])
def main():
    root=project_root(); R=root/'results'; D=R/'diagnostics'; E=R/'extension'; C=R/'country_replication_B1000'; O=R/'publication_frl'; O.mkdir(parents=True,exist_ok=True)
    p=json.loads((R/'primary_17_definitive_B2000/summary.json').read_text()); pi=json.loads((R/'primary_17_definitive_B2000/outer_bootstrap_intervals.json').read_text()); c=json.loads((C/'summary.json').read_text()); ci=json.loads((C/'outer_bootstrap_intervals.json').read_text())
    t1=pd.DataFrame([['17 U.S. industries',84,bp(p['mean_endpoint_loss']),f'[{bp(pi["baseline_mean_endpoint_loss"][0])}, {bp(pi["baseline_mean_endpoint_loss"][1])}]',bp(p['median_endpoint_loss']),bp(p['p75_endpoint_loss']),bp(p['p90_endpoint_loss']),pct(p['literal_switch_frequency'])],['14 developed-country markets',36,bp(c['mean_endpoint_loss']),f'[{bp(ci["mean_endpoint_loss"][0])}, {bp(ci["mean_endpoint_loss"][1])}]',bp(c['median_endpoint_loss']),bp(c['p75_endpoint_loss']),bp(c['p90_endpoint_loss']),pct(c['literal_switch_frequency'])]],columns=['Universe','Endpoint pairs','Mean loss (bp)','95% CI (bp)','Median','P75','P90','Switching (%)'])
    t1.to_csv(O/'table_1.csv',index=False); tex(t1,O/'table_1.tex','Endpoint reproducibility','tab:endpoint')
    t2=pd.DataFrame([['17 U.S. industries',75,pct(p['selector_hit_rate']),bp(p['mean_selection_regret']),f'[{bp(pi["baseline_mean_selection_regret"][0])}, {bp(pi["baseline_mean_selection_regret"][1])}]',bp(p['mean_selector_minus_ensemble']),f'[{bp(pi["baseline_mean_selector_minus_ensemble"][0])}, {bp(pi["baseline_mean_selector_minus_ensemble"][1])}]'],['14 developed-country markets',27,pct(c['selector_hit_rate']),bp(c['mean_selection_regret']),f'[{bp(ci["mean_selection_regret"][0])}, {bp(ci["mean_selection_regret"][1])}]',bp(c['mean_selector_minus_ensemble']),f'[{bp(ci["mean_selector_minus_ensemble"][0])}, {bp(ci["mean_selector_minus_ensemble"][1])}'] ],columns=['Universe','Decision dates','Hit rate (%)','Selection regret (bp)','Regret CI (bp)','Selector minus ensemble (bp)','Difference CI (bp)'])
    t2.to_csv(O/'table_2.csv',index=False); tex(t2,O/'table_2.tex','Ex-ante recoverability','tab:recoverability')
    fig,axs=plt.subplots(1,2,figsize=(9,3.5),sharey=True,constrained_layout=True)
    specs=[('17 U.S. industries',D/'survival_origin_audit_17_baseline.csv',D/'material_origin_audit_17_baseline.csv'),('14 developed-country markets',E/'countries_literal_origin_audit.csv',E/'countries_material25_origin_audit.csv')]
    for ax,(title,l,m) in zip(axs,specs):
        for label,path in [('Literal',l),('Material >25 bp',m)]:
            q=curve(pd.read_csv(path)); ax.step([0,*q.time_months],[1,*q.survival],where='post',label=label)
        ax.set_title(title); ax.set(xlabel='Months since December origin',ylim=(0,1.02)); ax.legend(frameon=False,fontsize=8)
    axs[0].set_ylabel('First-failure survival'); fig.savefig(O/'figure_1_winner_durability.pdf'); fig.savefig(O/'figure_1_winner_durability.png',dpi=220); plt.close(fig)
    # Lean appendix objects.
    sens=pd.read_csv(E/'primary17_gamma_cost_sensitivity.csv'); mat=pd.read_csv(E/'materiality_threshold_sensitivity.csv'); a1=pd.concat([sens.assign(panel='primary sensitivity'),mat.assign(panel='materiality threshold')],ignore_index=True).round(4); a1.to_csv(O/'table_A1_robustness.csv',index=False); tex(a1,O/'table_A1_robustness.tex','Robustness summary','tab:robustness')
    disp=pd.concat([pd.read_csv(E/'primary17_displacement.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_displacement.csv').assign(universe='countries')]).round(4); disp.to_csv(O/'table_A2_displacement_granularity.csv',index=False); tex(disp,O/'table_A2_displacement_granularity.tex','Endpoint displacement and granularity','tab:displacement')
    a3=pd.concat([pd.read_csv(E/'primary17_winner_conditioned.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_winner_conditioned.csv').assign(universe='countries')]).round(4); a3.to_csv(O/'table_A3_method_diagnostics.csv',index=False); tex(a3,O/'table_A3_method_diagnostics.tex','Method-conditioned outcomes','tab:methods')
    loo=pd.concat([pd.read_csv(E/'primary17_leave_one_out.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_leave_one_out.csv').assign(universe='countries')]).round(4); loo.to_csv(O/'figure_A2_leave_one_out_source.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(10,3.8),constrained_layout=True)
    for ax,(u,g) in zip(axs,loo.groupby('universe')): ax.bar(g.omitted_asset,10000*g.mean_endpoint_loss); ax.tick_params(axis='x',rotation=70,labelsize=7); ax.set(title=u,ylabel='Mean endpoint loss (bp)')
    fig.savefig(O/'figure_A2_leave_one_out.pdf'); fig.savefig(O/'figure_A2_leave_one_out.png',dpi=220); plt.close(fig)
    a4=pd.read_csv(E/'country_bootstrap_B1000_summary.csv').round(2); a4.to_csv(O/'table_A4_bootstrap_audit.csv',index=False); tex(a4,O/'table_A4_bootstrap_audit.tex','Country bootstrap audit','tab:bootstrap')
    for name,file in [('17 industries',E/'primary17_transition_row_percent.csv'),('14 countries',E/'countries_transition_row_percent.csv')]:
        q=pd.read_csv(file,index_col=0).fillna(0)*100; fig,ax=plt.subplots(figsize=(5,4),constrained_layout=True); im=ax.imshow(q); ax.set(title=name,xticks=range(5),xticklabels=q.columns,yticks=range(5),yticklabels=q.index); plt.setp(ax.get_xticklabels(),rotation=45,ha='right'); fig.colorbar(im,ax=ax,label='Row percentage'); fig.savefig(O/f'figure_A1_transition_{name.split()[0]}.pdf'); plt.close(fig)
    (O/'README.md').write_text('# Lean FRL bundle\n\nMain text: Table 1, Figure 1, Table 2. The margin diagnostic is reported in prose; its detailed CSV remains under results/extension. Appendix CSVs are compact source tables for typesetting.\n',encoding='utf8')
if __name__=='__main__': main()
