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
    t1=pd.DataFrame([['Endpoint pairs',84,36],['Mean endpoint loss (bp)',f'{bp(p["mean_endpoint_loss"]):.2f}',f'{bp(c["mean_endpoint_loss"]):.2f}'],['95% bootstrap CI (bp)',f'[{bp(pi["baseline_mean_endpoint_loss"][0]):.2f}, {bp(pi["baseline_mean_endpoint_loss"][1]):.2f}]',f'[{bp(ci["mean_endpoint_loss"][0]):.2f}, {bp(ci["mean_endpoint_loss"][1]):.2f}]'],['Median (bp)','0.00','0.00'],['P75 (bp)',f'{bp(p["p75_endpoint_loss"]):.2f}',f'{bp(c["p75_endpoint_loss"]):.2f}'],['P90 (bp)',f'{bp(p["p90_endpoint_loss"]):.2f}',f'{bp(c["p90_endpoint_loss"]):.2f}'],['Literal switching',f'{pct(p["literal_switch_frequency"]):.1f}%',f'{pct(c["literal_switch_frequency"]):.1f}%']],columns=['Metric','17 U.S. industries','14 developed-country markets'])
    t1.to_csv(O/'table_1.csv',index=False); tex(t1,O/'table_1.tex','Endpoint reproducibility','tab:endpoint')
    t2=pd.DataFrame([['Decision dates',75,27],['Selector hit rate',f'{pct(p["selector_hit_rate"]):.1f}%',f'{pct(c["selector_hit_rate"]):.1f}%'],['Selection regret (bp)',f'{bp(p["mean_selection_regret"]):.2f}',f'{bp(c["mean_selection_regret"]):.2f}'],['95% CI (regret, bp)',f'[{bp(pi["baseline_mean_selection_regret"][0]):.2f}, {bp(pi["baseline_mean_selection_regret"][1]):.2f}]',f'[{bp(ci["mean_selection_regret"][0]):.2f}, {bp(ci["mean_selection_regret"][1]):.2f}]'],['Selector minus ensemble (bp)',f'{bp(p["mean_selector_minus_ensemble"]):+.2f}',f'{bp(c["mean_selector_minus_ensemble"]):+.2f}'],['95% CI (difference, bp)',f'[{bp(pi["baseline_mean_selector_minus_ensemble"][0]):.2f}, {bp(pi["baseline_mean_selector_minus_ensemble"][1]):.2f}]',f'[{bp(ci["mean_selector_minus_ensemble"][0]):.2f}, {bp(ci["mean_selector_minus_ensemble"][1]):.2f}]']],columns=['Metric','17 U.S. industries','14 developed-country markets'])
    t2.to_csv(O/'table_2.csv',index=False); tex(t2,O/'table_2.tex','Ex-ante recoverability','tab:recoverability')
    fig,axs=plt.subplots(1,2,figsize=(9,3.5),sharey=True,constrained_layout=True)
    specs=[('17 U.S. industries',D/'survival_origin_audit_17_baseline.csv',D/'material_origin_audit_17_baseline.csv'),('14 developed-country markets',E/'countries_literal_origin_audit.csv',E/'countries_material25_origin_audit.csv')]
    handles=[]
    for ax,(title,l,m) in zip(axs,specs):
        for label,path in [('Literal',l),('Material >25 bp',m)]:
            q=curve(pd.read_csv(path)); line=ax.step([0,*q.time_months],[1,*q.survival],where='post',label='Material (>25 bp)' if label.startswith('Material') else label); handles.extend(line if not handles else [])
        ax.set_title(title); ax.set(xlabel='Months since December origin',xlim=(0,150),ylim=(0,1.02))
    axs[0].set_ylabel('Winner survival probability'); h,l=axs[0].get_legend_handles_labels(); fig.legend(h,l,loc='upper center',ncol=2,frameon=False); fig.savefig(O/'figure_1_winner_durability.pdf'); fig.savefig(O/'figure_1_winner_durability.png',dpi=220); plt.close(fig)
    # Lean appendix objects.
    sens=pd.read_csv(E/'primary17_gamma_cost_sensitivity.csv'); mat=pd.read_csv(E/'materiality_threshold_sensitivity.csv')
    a1a=sens[['setting','mean_endpoint_loss','median_endpoint_loss','literal_switch_frequency','loss_exceeds_25bp_frequency','survival_12_complete_followup','survival_24_complete_followup','median_survival_months_full_km']].copy()
    for col in ['mean_endpoint_loss','median_endpoint_loss']: a1a[col]*=10000
    for col in ['literal_switch_frequency','loss_exceeds_25bp_frequency','survival_12_complete_followup','survival_24_complete_followup']: a1a[col]*=100
    a1a=a1a.round(2); a1a.columns=['Setting','Mean loss (bp)','Median loss (bp)','Switching (%)','Loss >25 bp (%)','S(12) (%)','S(24) (%)','Median survival (months)']
    a1b=mat[['universe','threshold_bp','survival_12_complete_followup','survival_24_complete_followup','median_survival_months_full_km']].round(4)
    a1b.columns=['Universe','Threshold (bp)','S(12)','S(24)','Median survival (months)']
    a1a.to_csv(O/'table_A1_panel_A_specification_sensitivity.csv',index=False); a1b.to_csv(O/'table_A1_panel_B_materiality_thresholds.csv',index=False)
    tex(a1a,O/'table_A1_panel_A_specification_sensitivity.tex','Robustness summary: specification sensitivity','tab:robustness-specification'); tex(a1b,O/'table_A1_panel_B_materiality_thresholds.tex','Robustness summary: materiality thresholds','tab:robustness-materiality')
    disp=pd.concat([pd.read_csv(E/'primary17_displacement.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_displacement.csv').assign(universe='countries')]).copy()
    for col in ['mean_endpoint_loss','median_endpoint_loss','p75_endpoint_loss','p90_endpoint_loss']: disp[col]*=10000
    for col in ['literal_switch_frequency','loss_exceeds_25bp_frequency']: disp[col]*=100
    disp=disp[['universe','h','sample','mean_endpoint_loss','p90_endpoint_loss','literal_switch_frequency','loss_exceeds_25bp_frequency','n_origins']].round(2)
    disp.columns=['Universe','h (months)','Sample','Mean loss (bp)','P90 (bp)','Switching (%)','Loss >25 bp (%)','n']; disp.to_csv(O/'table_A2_displacement_granularity.csv',index=False); tex(disp,O/'table_A2_displacement_granularity.tex','Endpoint displacement and granularity','tab:displacement')
    a3=pd.concat([pd.read_csv(E/'primary17_winner_conditioned.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_winner_conditioned.csv').assign(universe='countries')]).copy(); a3['mean_endpoint_loss']*=10000; a3['switch_frequency']*=100; a3['loss_exceeds_25bp']*=100; a3=a3.round(2); a3.columns=['Winner','Origins','Switching (%)','Mean loss (bp)','Median loss','Loss >25 bp (%)','Universe']; a3.to_csv(O/'table_A3_method_diagnostics.csv',index=False); tex(a3,O/'table_A3_method_diagnostics.tex','Method-conditioned outcomes','tab:methods')
    loo=pd.concat([pd.read_csv(E/'primary17_leave_one_out.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_leave_one_out.csv').assign(universe='countries')]).round(4); loo.to_csv(O/'figure_A2_leave_one_out_source.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(10,3.8),constrained_layout=True)
    for ax,(u,g) in zip(axs,loo.groupby('universe')): ax.bar(g.omitted_asset,10000*g.mean_endpoint_loss); ax.tick_params(axis='x',rotation=70,labelsize=7); ax.set(title=u,ylabel='Mean endpoint loss (bp)')
    fig.savefig(O/'figure_A2_leave_one_out.pdf'); fig.savefig(O/'figure_A2_leave_one_out.png',dpi=220); plt.close(fig)
    a4=pd.read_csv(E/'country_bootstrap_B1000_summary.csv').round(2); a4.to_csv(O/'table_A4_bootstrap_audit.csv',index=False); tex(a4,O/'table_A4_bootstrap_audit.tex','Country bootstrap audit','tab:bootstrap')
    for name,file in [('17 industries',E/'primary17_transition_row_percent.csv'),('14 countries',E/'countries_transition_row_percent.csv')]:
        q=pd.read_csv(file,index_col=0).fillna(0)*100; fig,ax=plt.subplots(figsize=(5,4),constrained_layout=True); im=ax.imshow(q); ax.set(title=name,xticks=range(5),xticklabels=q.columns,yticks=range(5),yticklabels=q.index); plt.setp(ax.get_xticklabels(),rotation=45,ha='right'); fig.colorbar(im,ax=ax,label='Row percentage'); fig.savefig(O/f'figure_A1_transition_{name.split()[0]}.pdf'); plt.close(fig)
    methods=pd.DataFrame([['Equal weight','None','Equal weights','Long-only, fully invested','60 months','Monthly'],['Sample GMV','Sample covariance','Minimum variance','Long-only, fully invested','60 months','Monthly'],['Ledoit--Wolf GMV','Shrinkage covariance','Minimum variance','Long-only, fully invested','60 months','Monthly'],['Inverse volatility','Sample volatility','Inverse volatility weights','Long-only, fully invested','60 months','Monthly'],['ERC','Sample covariance','Equal risk contributions','Long-only, fully invested','60 months','Monthly']],columns=['Method','Risk input','Rule/objective','Constraints','Lookback','Rebalance'])
    datasets=pd.DataFrame([['17 U.S. industries',17,'Kenneth French','1926-07--2026-07','1931-07',84,75,'USD'],['14 developed-country markets',14,'Kenneth French international','1975-01--2025-12','1980-01',36,27,'USD'],['30 U.S. industries',30,'Kenneth French','1926-07--2026-07','1931-07',84,75,'USD']],columns=['Universe','Assets','Source','Sample','OOS start','Endpoint pairs','Ex-ante dates','Currency'])
    methods.to_csv(O/'table_A5_panel_A_methods.csv',index=False); datasets.to_csv(O/'table_A5_panel_B_data.csv',index=False); tex(methods,O/'table_A5_panel_A_methods.tex','Portfolio methods and sample construction: methods','tab:methods-reference'); tex(datasets,O/'table_A5_panel_B_data.tex','Portfolio methods and sample construction: datasets','tab:data-reference')
    (O/'README.md').write_text('# Lean FRL bundle\n\nMain text: Table 1, Figure 1, Table 2. The margin diagnostic is reported in prose; its detailed CSV remains under results/extension. Appendix CSVs are compact source tables for typesetting.\n',encoding='utf8')
if __name__=='__main__': main()
