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
    # Remove names superseded by the consolidated appendix objects on reruns.
    for stale in ['figure_A1_transition_14.pdf','figure_A1_transition_17.pdf','table_A4_bootstrap_audit.csv','table_A4_bootstrap_audit.tex']:
        (O/stale).unlink(missing_ok=True)
    p=json.loads((R/'primary_17_definitive_B2000/summary.json').read_text()); pi=json.loads((R/'primary_17_definitive_B2000/outer_bootstrap_intervals.json').read_text()); c=json.loads((C/'summary.json').read_text()); ci=json.loads((C/'outer_bootstrap_intervals.json').read_text())
    t1=pd.DataFrame([['Endpoint pairs',84,36],['Mean endpoint loss (bp)',f'{bp(p["mean_endpoint_loss"]):.2f}',f'{bp(c["mean_endpoint_loss"]):.2f}'],['95% bootstrap CI (bp)',f'[{bp(pi["baseline_mean_endpoint_loss"][0]):.2f}, {bp(pi["baseline_mean_endpoint_loss"][1]):.2f}]',f'[{bp(ci["mean_endpoint_loss"][0]):.2f}, {bp(ci["mean_endpoint_loss"][1]):.2f}]'],['Median (bp)','0.00','0.00'],['P75 (bp)',f'{bp(p["p75_endpoint_loss"]):.2f}',f'{bp(c["p75_endpoint_loss"]):.2f}'],['P90 (bp)',f'{bp(p["p90_endpoint_loss"]):.2f}',f'{bp(c["p90_endpoint_loss"]):.2f}'],['Literal switching',f'{pct(p["literal_switch_frequency"]):.1f}%',f'{pct(c["literal_switch_frequency"]):.1f}%']],columns=['Metric','17 U.S. industries','14 developed-country markets'])
    t1.to_csv(O/'table_1.csv',index=False); tex(t1,O/'table_1.tex','Endpoint reproducibility','tab:endpoint')
    t2=pd.DataFrame([['Decision dates',75,27],['Selector hit rate',f'{pct(p["selector_hit_rate"]):.1f}%',f'{pct(c["selector_hit_rate"]):.1f}%'],['Selection regret (bp)',f'{bp(p["mean_selection_regret"]):.2f}',f'{bp(c["mean_selection_regret"]):.2f}'],['95% CI (regret, bp)',f'[{bp(pi["baseline_mean_selection_regret"][0]):.2f}, {bp(pi["baseline_mean_selection_regret"][1]):.2f}]',f'[{bp(ci["mean_selection_regret"][0]):.2f}, {bp(ci["mean_selection_regret"][1]):.2f}]'],['Selector minus ensemble (bp)',f'{bp(p["mean_selector_minus_ensemble"]):+.2f}',f'{bp(c["mean_selector_minus_ensemble"]):+.2f}'],['95% CI (difference, bp)',f'[{bp(pi["baseline_mean_selector_minus_ensemble"][0]):.2f}, {bp(pi["baseline_mean_selector_minus_ensemble"][1]):.2f}]',f'[{bp(ci["mean_selector_minus_ensemble"][0]):.2f}, {bp(ci["mean_selector_minus_ensemble"][1]):.2f}]']],columns=['Metric','17 U.S. industries','14 developed-country markets'])
    t2.to_csv(O/'table_2.csv',index=False); tex(t2,O/'table_2.tex','Ex-ante recoverability','tab:recoverability')
    fig,axs=plt.subplots(1,2,figsize=(9,3.5),sharey=True)
    fig.subplots_adjust(left=.08,right=.99,bottom=.18,top=.80,wspace=.035)
    specs=[('17 U.S. industries',D/'survival_origin_audit_17_baseline.csv',D/'material_origin_audit_17_baseline.csv'),('14 developed-country markets',E/'countries_literal_origin_audit.csv',E/'countries_material25_origin_audit.csv')]
    handles=[]
    for ax,(title,l,m) in zip(axs,specs):
        for label,path in [('Literal',l),('Material >25 bp',m)]:
            q=curve(pd.read_csv(path)); line=ax.step([0,*q.time_months],[1,*q.survival],where='post',label='Material (>25 bp)' if label.startswith('Material') else label); handles.extend(line if not handles else [])
        ax.set_title(title); ax.set(xlabel='Months since December origin',xlim=(0,150),ylim=(0,1.02))
    axs[0].set_ylabel('Censored-KM winner survival probability'); h,l=axs[0].get_legend_handles_labels(); fig.legend(h,l,loc='upper center',bbox_to_anchor=(.5,.995),ncol=2,frameon=False); fig.savefig(O/'figure_1_winner_durability.pdf'); fig.savefig(O/'figure_1_winner_durability.png',dpi=220); plt.close(fig)
    # Lean appendix objects.
    sens=pd.read_csv(E/'primary17_gamma_cost_sensitivity.csv'); mat=pd.read_csv(E/'materiality_threshold_sensitivity.csv')
    extra=[]
    for rn,label in [('primary_17_L36','L=36'),('primary_17_L120','L=120'),('primary_17_quarterly','Quarterly')]:
        z=json.loads((R/rn/'summary.json').read_text()); extra.append({'setting':label,'mean_endpoint_loss':z['mean_endpoint_loss'],'literal_switch_frequency':z['literal_switch_frequency'],'loss_exceeds_25bp_frequency':float('nan'),'survival_12_complete_followup':z['survival_12_months'],'median_survival_months_full_km':z['median_survival_months']})
    sens=pd.concat([pd.DataFrame(extra),sens],ignore_index=True)
    a1a=sens[['setting','mean_endpoint_loss','literal_switch_frequency','loss_exceeds_25bp_frequency','survival_12_complete_followup','median_survival_months_full_km']].copy()
    for col in ['mean_endpoint_loss']: a1a[col]*=10000
    for col in ['literal_switch_frequency','loss_exceeds_25bp_frequency','survival_12_complete_followup']: a1a[col]*=100
    a1a=a1a.round(2); a1a.columns=['Setting','Mean loss (bp)','Switching (%)','Loss >25 bp (%)','Complete-follow-up S(12) (%)','Full-KM median survival (months)']
    # The L/rebalancing summaries do not store the 25-bp tail statistic.
    a1a['Loss >25 bp (%)']=a1a['Loss >25 bp (%)'].fillna('--')
    a1b=mat[['universe','threshold_bp','survival_12_complete_followup','survival_24_complete_followup','median_survival_months_full_km']].copy(); a1b['universe']=a1b['universe'].replace({'primary17':'17 U.S. industries','countries':'14 developed-country markets'}); a1b[['survival_12_complete_followup','survival_24_complete_followup']]*=100; a1b=a1b.round(1)
    a1b.columns=['Universe','Threshold (bp)','Complete-follow-up S(12) (%)','Complete-follow-up S(24) (%)','Full-KM median survival (months)']
    a1a.to_csv(O/'table_A1_panel_A_specification_sensitivity.csv',index=False); a1b.to_csv(O/'table_A1_panel_B_materiality_thresholds.csv',index=False)
    tex(a1a,O/'table_A1_panel_A_specification_sensitivity.tex','Robustness summary: specification sensitivity','tab:robustness-specification'); tex(a1b,O/'table_A1_panel_B_materiality_thresholds.tex','Robustness summary: materiality thresholds','tab:robustness-materiality')
    disp=pd.concat([pd.read_csv(E/'primary17_displacement.csv').assign(universe='17 U.S. industries'),pd.read_csv(E/'countries_displacement.csv').assign(universe='14 developed-country markets')]).copy()
    for col in ['mean_endpoint_loss','median_endpoint_loss','p75_endpoint_loss','p90_endpoint_loss']: disp[col]*=10000
    for col in ['literal_switch_frequency','loss_exceeds_25bp_frequency']: disp[col]*=100
    disp=disp[['universe','h','sample','mean_endpoint_loss','p90_endpoint_loss','literal_switch_frequency','loss_exceeds_25bp_frequency','n_origins']].round(2)
    disp.columns=['Universe','h (months)','Sample','Mean loss (bp)','P90 (bp)','Switching (%)','Loss >25 bp (%)','n']; disp.to_csv(O/'table_A2_displacement_granularity.csv',index=False)
    # Main Figure 2: the prespecified endpoint-displacement profile.
    fig,ax=plt.subplots(figsize=(6.5,3.8),constrained_layout=True)
    figure2=disp.loc[disp['Sample']=='full_eligible',['Universe','h (months)','Mean loss (bp)']].copy()
    for universe,g in figure2.groupby('Universe',sort=False):
        g=g.sort_values('h (months)'); ax.plot(g['h (months)'],g['Mean loss (bp)'],marker='o',linewidth=2,label=universe)
    ax.set(xlabel='Endpoint displacement (months)',ylabel='Mean endpoint loss (bp)',xticks=[6,12,24])
    ax.legend(frameon=False); fig.savefig(O/'figure_2_endpoint_displacement.pdf'); fig.savefig(O/'figure_2_endpoint_displacement.png',dpi=220); plt.close(fig)
    figure2.to_csv(O/'figure_2_endpoint_displacement_source.csv',index=False)
    for sample,title,stem in [('full_eligible','Endpoint displacement: full eligible origins','table_A2_panel_A_full'),('common_calendar_origins','Endpoint displacement: common calendar origins','table_A2_panel_B_common')]:
        q=disp.loc[disp.Sample==sample].drop(columns='Sample'); q.to_csv(O/f'{stem}.csv',index=False); tex(q,O/f'{stem}.tex',title,f'tab:{stem}')
    s30=json.loads((R/'replication_30_B1000/summary.json').read_text()); i30=json.loads((R/'replication_30_B1000/outer_bootstrap_intervals.json').read_text()); q30=pd.DataFrame([['30 U.S. industries',f'{bp(s30["mean_endpoint_loss"]):.2f}',f'[{bp(i30["mean_endpoint_loss"][0]):.2f}, {bp(i30["mean_endpoint_loss"][1]):.2f}]',f'{pct(s30["literal_switch_frequency"]):.1f}%',s30['median_survival_months']]])
    q30.columns=['Universe','Mean loss (bp)','95% CI (bp)','Switching','Literal median (months)']; q30.to_csv(O/'table_A2_panel_C_30industry.csv',index=False); tex(q30,O/'table_A2_panel_C_30industry.tex','30-industry granularity check','tab:granularity')
    labels={'equal_weight':'Equal weight','sample_gmv':'Sample GMV','ledoit_wolf_gmv':'Ledoit--Wolf GMV','inverse_volatility':'Inverse volatility','erc':'ERC'}; frames=[]
    for u,file in [('17 U.S. industries','primary17_winner_conditioned.csv'),('14 developed-country markets','countries_winner_conditioned.csv')]:
        q=pd.read_csv(E/file).set_index('original_winner').reindex(labels).reset_index(); q['universe']=u; frames.append(q)
    a3=pd.concat(frames); a3['original_winner']=a3.original_winner.map(labels); a3['mean_endpoint_loss']*=10000; a3['switch_frequency']*=100; a3['loss_exceeds_25bp']*=100; a3['sparse_note']=a3.n_origins.map(lambda n:'dagger: n<5' if pd.notna(n) and n<5 else ''); a3=a3.round(2); a3.columns=['Initial winner','Origins','Switching (%)','Mean loss (bp)','Median loss','Loss >25 bp (%)','Universe','Note']; a3=a3.fillna('--'); a3.to_csv(O/'table_A3_method_diagnostics.csv',index=False); tex(a3,O/'table_A3_method_diagnostics.tex','Method-conditioned outcomes. dagger indicates fewer than five origins.','tab:methods')
    loo=pd.concat([pd.read_csv(E/'primary17_leave_one_out.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_leave_one_out.csv').assign(universe='countries')])
    full_losses={'17 industries':p['mean_endpoint_loss'],'countries':c['mean_endpoint_loss']}
    loo['influence_shift_bp']=loo.apply(lambda x:10000*(x['mean_endpoint_loss']-full_losses[x['universe']]),axis=1)
    loo.to_csv(O/'figure_A2_leave_one_out_source.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(10,5),constrained_layout=True)
    for ax,(u,g) in zip(axs,loo.groupby('universe')): ax.plot(g.influence_shift_bp,range(len(g)),'o'); ax.axvline(0,ls='--',color='black'); ax.set(title='17 U.S. industries' if u=='17 industries' else '14 developed-country markets',yticks=range(len(g)),yticklabels=g.omitted_asset,xlabel='Change in mean endpoint loss (bp)')
    fig.savefig(O/'figure_A2_leave_one_out.pdf'); fig.savefig(O/'figure_A2_leave_one_out.png',dpi=220); plt.close(fig)
    # A4 panel A: endpoint inference under each resampling law.
    bootstrap_rows=[]
    for name,design,folder,reps,key in [
        ('17 U.S. industries','Stationary bootstrap','primary_17_definitive_B2000',2000,'baseline_mean_endpoint_loss'),
        ('17 U.S. industries','Fixed circular blocks (12 months)','primary_17_fixedblock12_B1000',1000,'mean_endpoint_loss'),
        ('17 U.S. industries','Fixed circular blocks (24 months)','primary_17_fixedblock24_B1000',1000,'mean_endpoint_loss'),
        ('14 developed-country markets','Stationary bootstrap','country_replication_B1000',1000,'mean_endpoint_loss'),
    ]:
        s=json.loads((R/folder/'summary.json').read_text()); interval=json.loads((R/folder/'outer_bootstrap_intervals.json').read_text())[key]
        bootstrap_rows.append([name,design,reps,bp(s['mean_endpoint_loss']),f'[{bp(interval[0]):.2f}, {bp(interval[1]):.2f}]'])
    a4a=pd.DataFrame(bootstrap_rows,columns=['Universe','Bootstrap design','B','Endpoint loss (bp)','95% CI (bp)']).round(2)
    a4a.to_csv(O/'table_A4_panel_A_endpoint_inference.csv',index=False); tex(a4a,O/'table_A4_panel_A_endpoint_inference.tex','Bootstrap audit: endpoint-loss inference','tab:bootstrap-endpoint')
    a4b=pd.read_csv(E/'country_bootstrap_B1000_summary.csv')[['metric','point_estimate','ci_low','ci_high','unit','bootstrap_replications']].copy()
    a4b['Estimate']=a4b.apply(lambda x:f"{x.point_estimate:.2f}",axis=1); a4b['95% CI']=a4b.apply(lambda x:f"[{x.ci_low:.2f}, {x.ci_high:.2f}]",axis=1)
    a4b=a4b[['metric','Estimate','95% CI','unit','bootstrap_replications']]; a4b.columns=['Country statistic','Estimate','95% CI','Unit','B']
    a4b.to_csv(O/'table_A4_panel_B_country_secondary.csv',index=False); tex(a4b,O/'table_A4_panel_B_country_secondary.tex','Bootstrap audit: country secondary outcomes','tab:bootstrap-country')
    # Figure A1: two transition matrices, directly comparable on a 0--100 scale.
    matrices=[]
    for name,file,winner_file in [('17 U.S. industries',E/'primary17_transition_row_percent.csv',E/'primary17_winner_conditioned.csv'),('14 developed-country markets',E/'countries_transition_row_percent.csv',E/'countries_winner_conditioned.csv')]:
        q=pd.read_csv(file,index_col=0).reindex(index=labels,columns=labels)
        counts=pd.read_csv(winner_file).set_index('original_winner')['n_origins'].reindex(labels).fillna(0).astype(int)
        matrices.append((name,q,counts))
    fig,axs=plt.subplots(1,2,figsize=(11,4.6),constrained_layout=True)
    for ax,(name,q,counts) in zip(axs,matrices):
        values=q.fillna(0).to_numpy()*100; im=ax.imshow(values,vmin=0,vmax=100,cmap='Blues')
        for i in range(5):
            for j in range(5):
                cell='--' if pd.isna(q.iloc[i,j]) else f'{values[i,j]:.0f}'
                ax.text(j,i,cell,ha='center',va='center',fontsize=8,color='white' if values[i,j]>=55 else 'black')
        ax.set(title=name,xticks=range(5),xticklabels=[labels[x] for x in q.columns],yticks=range(5),yticklabels=[f'{labels[x]} (n={counts[x]})' for x in q.index],xlabel='Winner 12 months later',ylabel='Initial winner')
        plt.setp(ax.get_xticklabels(),rotation=38,ha='right')
    fig.colorbar(im,ax=axs,label='Row percentage',shrink=.85); fig.savefig(O/'figure_A1_transition_matrices.pdf'); fig.savefig(O/'figure_A1_transition_matrices.png',dpi=220); plt.close(fig)
    methods=pd.DataFrame([['Equal weight','None','Equal weights','Long-only, fully invested','60 months','Monthly'],['Sample GMV','Sample covariance','Minimum variance','Long-only, fully invested','60 months','Monthly'],['Ledoit--Wolf GMV','Shrinkage covariance','Minimum variance','Long-only, fully invested','60 months','Monthly'],['Inverse volatility','Sample volatility','Inverse volatility weights','Long-only, fully invested','60 months','Monthly'],['ERC','Sample covariance','Equal risk contributions','Long-only, fully invested','60 months','Monthly']],columns=['Method','Risk input','Rule/objective','Constraints','Lookback','Rebalance'])
    datasets=pd.DataFrame([['17 U.S. industries',17,'Kenneth French','1926-07--2026-07','1931-07',84,75,'USD'],['14 developed-country markets',14,'Kenneth French international','1975-01--2025-12','1980-01',36,27,'USD'],['30 U.S. industries',30,'Kenneth French','1926-07--2026-07','1931-07',84,75,'USD']],columns=['Universe','Assets','Source','Sample','OOS start','Endpoint pairs','Ex-ante dates','Currency'])
    methods.to_csv(O/'table_A5_panel_A_methods.csv',index=False); datasets.to_csv(O/'table_A5_panel_B_data.csv',index=False); tex(methods,O/'table_A5_panel_A_methods.tex','Portfolio methods and sample construction: methods','tab:methods-reference'); tex(datasets,O/'table_A5_panel_B_data.tex','Portfolio methods and sample construction: datasets','tab:data-reference')
    (O/'README.md').write_text('# Lean FRL bundle\n\nMain text: Table 1, Figure 1 (censored-KM winner durability), Figure 2 (descriptive endpoint displacement), and Table 2. Appendix Table A1 labels complete-follow-up survival separately from full Kaplan--Meier medians. The margin diagnostic remains a reproducibility artifact under results/extension.\n',encoding='utf8')
if __name__=='__main__': main()
