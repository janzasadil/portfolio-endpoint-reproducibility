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
def tabular(df):
    d=df.copy()
    d.columns=[str(c).replace('%',r'\%').replace('_',r'\_') for c in d.columns]
    for c in d:
        if d[c].dtype=='object': d[c]=d[c].map(lambda v:v.replace('%',r'\%').replace('_',r'\_') if isinstance(v,str) else v)
    return d.to_latex(index=False,escape=False,float_format=lambda x:f'{x:.2f}')
def tex(df,path,caption,label):
    path.write_text('\\begin{table}[!htbp]\n\\centering\n\\small\n\\caption{'+caption+'}\n\\label{'+label+'}\n'+tabular(df)+'\\end{table}\n',encoding='utf8')
def fragment(df,path): path.write_text(tabular(df),encoding='utf8')
def parent_table(path,caption,label,panels):
    body=['\\begin{table}[!htbp]','\\centering','\\small',f'\\caption{{{caption}}}',f'\\label{{{label}}}']
    for heading,filename in panels:
        body.extend([f'\\textit{{{heading}}}',f'\\input{{{filename}}}','\\vspace{0.8em}'])
    body.append('\\end{table}')
    path.write_text('\n'.join(body)+'\n',encoding='utf8')
def curve(audit): return kaplan_meier(audit.rename(columns={'survival_duration_months':'time_months'})[['time_months','event']])
def main():
    root=project_root(); R=root/'results'; D=R/'diagnostics'; E=R/'extension'; C=R/'country_replication_B1000'; O=R/'publication_frl'; O.mkdir(parents=True,exist_ok=True)
    # Remove names superseded by the consolidated appendix objects on reruns.
    for stale in ['figure_A1_transition_14.pdf','figure_A1_transition_17.pdf','figure_A3_endpoint_displacement.pdf','figure_A3_endpoint_displacement.png','figure_A3_endpoint_displacement_source.csv','table_A2_displacement_granularity.csv','table_A2_displacement_granularity.tex','table_A2_panel_A_full.csv','table_A2_panel_A_full.tex','table_A2_panel_B_common.csv','table_A2_panel_B_common.tex','table_A2_panel_C_30industry.csv','table_A2_panel_C_30industry.tex','table_A3_method_diagnostics.csv','table_A3_method_diagnostics.tex','table_A4_bootstrap_audit.csv','table_A4_bootstrap_audit.tex']:
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
    a1a_tex=tabular(a1a).replace('\\midrule\n','\\midrule\n\\multicolumn{6}{l}{\\textit{Estimation / rebalancing}} \\\\\n',1).replace('gamma2 &','\\multicolumn{6}{l}{\\textit{Risk aversion}} \\\\\ngamma2 &').replace('cost0 &','\\multicolumn{6}{l}{\\textit{Transaction costs}} \\\\\ncost0 &')
    (O/'table_A1_panel_A_specification_sensitivity.tex').write_text(a1a_tex,encoding='utf8'); fragment(a1b,O/'table_A1_panel_B_materiality_thresholds.tex')
    parent_table(O/'table_A1.tex','Robustness to specification choices','tab:robustness',[('Panel A. Implementation and preference sensitivity','table_A1_panel_A_specification_sensitivity.tex'),('Panel B. Economic-materiality threshold','table_A1_panel_B_materiality_thresholds.tex')])
    disp=pd.concat([pd.read_csv(E/'primary17_displacement.csv').assign(universe='17 U.S. industries'),pd.read_csv(E/'countries_displacement.csv').assign(universe='14 developed-country markets')]).copy()
    for col in ['mean_endpoint_loss','median_endpoint_loss','p75_endpoint_loss','p90_endpoint_loss']: disp[col]*=10000
    for col in ['literal_switch_frequency','loss_exceeds_25bp_frequency']: disp[col]*=100
    disp=disp[['universe','h','sample','mean_endpoint_loss','p90_endpoint_loss','literal_switch_frequency','loss_exceeds_25bp_frequency','n_origins']].round(2)
    disp.columns=['Universe','h (months)','Sample','Mean loss (bp)','P90 (bp)','Switching (%)','Loss >25 bp (%)','n']; disp.to_csv(O/'source_A2_displacement_all.csv',index=False)
    # Main Figure 2: descriptive profiles at the three prespecified horizons.
    figure2=disp.loc[disp['Sample']=='full_eligible',['Universe','h (months)','Mean loss (bp)']].copy()
    fig,ax=plt.subplots(figsize=(6.5,3.8),constrained_layout=True)
    colors={'17 U.S. industries':'tab:blue','14 developed-country markets':'tab:orange'}
    for universe,g in figure2.groupby('Universe',sort=False):
        g=g.sort_values('h (months)'); line=ax.plot(g['h (months)'],g['Mean loss (bp)'],marker='o',linewidth=2,color=colors[universe])[0]
        ax.annotate(universe,xy=(24,g['Mean loss (bp)'].iloc[-1]),xytext=(7,0),textcoords='offset points',va='center',color=line.get_color(),fontsize=9)
    ax.set(xlabel='Endpoint displacement (months)',ylabel='Mean endpoint loss (CEQ bp)',xticks=[6,12,24])
    fig.savefig(O/'figure_2_endpoint_displacement.pdf'); fig.savefig(O/'figure_2_endpoint_displacement.png',dpi=220); plt.close(fig)
    figure2.to_csv(O/'figure_2_endpoint_displacement_source.csv',index=False)
    # Retain the paired primary horizon intervals as an inference table, not
    # unequal visual ornamentation on the two-universe descriptive profile.
    primary_draws=pd.read_csv(R/'primary_17_definitive_B2000/outer_bootstrap.csv')
    primary_columns={6:'h6_mean_endpoint_loss',12:'baseline_mean_endpoint_loss',24:'h24_mean_endpoint_loss'}
    primary_intervals={h:(10000*primary_draws[column].quantile(.025),10000*primary_draws[column].quantile(.975)) for h,column in primary_columns.items()}
    q_common=disp.loc[disp.Sample=='common_calendar_origins'].drop(columns='Sample'); q_common.to_csv(O/'table_A2_panel_A_common_origin.csv',index=False); fragment(q_common,O/'table_A2_panel_A_common_origin.tex')
    s30=json.loads((R/'replication_30_B1000/summary.json').read_text()); i30=json.loads((R/'replication_30_B1000/outer_bootstrap_intervals.json').read_text()); q30=pd.DataFrame([['30 U.S. industries',f'{bp(s30["mean_endpoint_loss"]):.2f}',f'[{bp(i30["mean_endpoint_loss"][0]):.2f}, {bp(i30["mean_endpoint_loss"][1]):.2f}]',f'{pct(s30["literal_switch_frequency"]):.1f}%',s30['median_survival_months']]])
    q30.columns=['Universe','Mean loss (bp)','95% CI (bp)','Switching','Literal median (months)']; q30.to_csv(O/'table_A2_panel_B_30industry.csv',index=False); fragment(q30,O/'table_A2_panel_B_30industry.tex')
    parent_table(O/'table_A2.tex','Additional robustness across horizons and universes','tab:additional-robustness',[('Panel A. Common-origin endpoint-displacement robustness','table_A2_panel_A_common_origin.tex'),('Panel B. 30-industry granularity check','table_A2_panel_B_30industry.tex')])
    labels={'equal_weight':'Equal weight','sample_gmv':'Sample GMV','ledoit_wolf_gmv':'Ledoit--Wolf GMV','inverse_volatility':'Inverse volatility','erc':'ERC'}; frames=[]
    for u,file in [('17 U.S. industries','primary17_winner_conditioned.csv'),('14 developed-country markets','countries_winner_conditioned.csv')]:
        q=pd.read_csv(E/file).set_index('original_winner').reindex(labels).reset_index(); q['universe']=u; frames.append(q)
    a3=pd.concat(frames); a3['original_winner']=a3.original_winner.map(labels); a3['mean_endpoint_loss']*=10000; a3['switch_frequency']*=100; a3['loss_exceeds_25bp']*=100; a3=a3.round(2)
    a3['Initial winner']=a3.apply(lambda x:f"{x.original_winner}\\textsuperscript{{\\(\\dagger\\)}}" if pd.notna(x.n_origins) and x.n_origins<5 else x.original_winner,axis=1)
    a3=a3[['Initial winner','n_origins','switch_frequency','mean_endpoint_loss','loss_exceeds_25bp','universe']].fillna('--')
    a3.columns=['Initial winner','Origins','Switching (%)','Mean loss (bp)','Loss >25 bp (%)','Universe']
    a3.to_csv(O/'source_A3_method_diagnostics_all.csv',index=False)
    a3_us=a3.loc[a3['Universe']=='17 U.S. industries'].drop(columns='Universe'); a3_country=a3.loc[a3['Universe']=='14 developed-country markets'].drop(columns='Universe')
    fragment(a3_us,O/'table_A3_panel_A_us_industries.tex'); fragment(a3_country,O/'table_A3_panel_B_countries.tex')
    parent_table(O/'table_A3.tex','Method-conditioned diagnostics. \\(\\dagger\\) indicates fewer than five eligible origins; conditional statistics are descriptive only.','tab:methods',[('Panel A. 17 U.S. industries','table_A3_panel_A_us_industries.tex'),('Panel B. 14 developed-country markets','table_A3_panel_B_countries.tex')])
    loo=pd.concat([pd.read_csv(E/'primary17_leave_one_out.csv').assign(universe='17 industries'),pd.read_csv(E/'countries_leave_one_out.csv').assign(universe='countries')])
    full_losses={'17 industries':p['mean_endpoint_loss'],'countries':c['mean_endpoint_loss']}
    loo['influence_shift_bp']=loo.apply(lambda x:10000*(x['mean_endpoint_loss']-full_losses[x['universe']]),axis=1)
    loo.to_csv(O/'figure_A2_leave_one_out_source.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(10,5),constrained_layout=True)
    fig.suptitle('Leave-one-out sensitivity of mean endpoint loss')
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
    a4a.to_csv(O/'table_A4_panel_A_endpoint_inference.csv',index=False); fragment(a4a,O/'table_A4_panel_A_endpoint_inference.tex')
    a4b=pd.read_csv(E/'country_bootstrap_B1000_summary.csv')[['metric','point_estimate','ci_low','ci_high','unit','bootstrap_replications']].copy()
    a4b['Estimate']=a4b.apply(lambda x:f"{x.point_estimate:.2f}",axis=1); a4b['95% CI']=a4b.apply(lambda x:f"[{x.ci_low:.2f}, {x.ci_high:.2f}]",axis=1)
    a4b=a4b[['metric','Estimate','95% CI','unit']]; a4b.columns=['Country statistic','Estimate','95% CI','Unit']
    a4b.to_csv(O/'table_A4_panel_B_country_secondary.csv',index=False); fragment(a4b,O/'table_A4_panel_B_country_secondary.tex')
    a4c=pd.DataFrame([[h,figure2.loc[(figure2['Universe']=='17 U.S. industries') & (figure2['h (months)']==h),'Mean loss (bp)'].iloc[0],f'[{low:.2f}, {high:.2f}]'] for h,(low,high) in primary_intervals.items()],columns=['Displacement (months)','Endpoint loss (CEQ bp)','95% CI (bp)']).round(2)
    a4c.to_csv(O/'table_A4_panel_C_primary_displacement_intervals.csv',index=False); fragment(a4c,O/'table_A4_panel_C_primary_displacement_intervals.tex')
    parent_table(O/'table_A4.tex','Bootstrap inference audit','tab:bootstrap',[('Panel A. Endpoint-loss inference','table_A4_panel_A_endpoint_inference.tex'),('Primary 17-industry displacement intervals','table_A4_panel_C_primary_displacement_intervals.tex'),('Panel B. Country secondary outcomes (all intervals use B=1,000 stationary-bootstrap replications)','table_A4_panel_B_country_secondary.tex')])
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
    methods.to_csv(O/'table_A5_panel_A_methods.csv',index=False); datasets.to_csv(O/'table_A5_panel_B_data.csv',index=False); fragment(methods,O/'table_A5_panel_A_methods.tex'); fragment(datasets,O/'table_A5_panel_B_data.tex')
    parent_table(O/'table_A5.tex','Portfolio methods and sample construction','tab:implementation-data',[('Panel A. Portfolio methods','table_A5_panel_A_methods.tex'),('Panel B. Data and analysis samples','table_A5_panel_B_data.tex')])
    (O/'README.md').write_text('# Lean FRL bundle\n\nMain text: Table 1, Figure 1 (censored-KM winner durability), Figure 2 (endpoint-displacement profiles), and Table 2. For the appendix, insert only `table_A1.tex` through `table_A5.tex`: these are the five publication-level floats. Their `table_A*_panel_*.tex` files are modular tabular-only fragments, not standalone floats. Appendix Table A4 includes the primary h=6/12/24 bootstrap intervals.\n',encoding='utf8')
    (O/'FIGURE_NOTES.md').write_text('# Figure captions and notes\n\n## Figure 2. Endpoint-displacement profiles\n\nPoints are deterministic mean endpoint losses at the prespecified displacement horizons. Lines connect the three reported horizons for visual guidance only; no functional form or monotonicity is estimated.\n\n## Figure A2. Leave-one-out sensitivity of mean endpoint loss\n\nEach point is the change in mean endpoint loss when the named asset is omitted, relative to the full universe. Removing an asset changes both portfolio composition and cross-sectional dimension; values are sensitivity diagnostics, not asset-specific causal contributions.\n',encoding='utf8')
if __name__=='__main__': main()
