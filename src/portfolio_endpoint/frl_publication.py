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
def tabular(df,column_format=None):
    d=df.copy()
    d.columns=[str(c).replace('%',r'\%').replace('_',r'\_') for c in d.columns]
    for c in d:
        if d[c].dtype=='object': d[c]=d[c].map(lambda v:v.replace('%',r'\%') if isinstance(v,str) and '$' in v else (v.replace('%',r'\%').replace('_',r'\_') if isinstance(v,str) else v))
    return d.to_latex(index=False,escape=False,column_format=column_format,float_format=lambda x:f'{x:.2f}')
def tex(df,path,caption,label,column_format=None):
    path.write_text('\\begin{table}[!htbp]\n\\centering\n\\small\n\\caption{'+caption+'}\n\\label{'+label+'}\n'+tabular(df,column_format)+'\\end{table}\n',encoding='utf8')
def fragment(df,path): path.write_text(tabular(df),encoding='utf8')
def parent_table(path,caption,label,panels):
    body=['\\begin{table}[!htbp]','\\centering','\\small',f'\\caption{{{caption}}}',f'\\label{{{label}}}']
    for heading,content in panels:
        body.extend([f'\\textit{{{heading}}}',content,'\\vspace{0.8em}'])
    body.append('\\end{table}')
    path.write_text('\n'.join(body)+'\n',encoding='utf8')
def curve(audit): return kaplan_meier(audit.rename(columns={'survival_duration_months':'time_months'})[['time_months','event']])
def main():
    root=project_root(); R=root/'results'; D=R/'diagnostics'; E=R/'extension'; C=R/'country_replication_B1000'; O=R/'publication_frl'; O.mkdir(parents=True,exist_ok=True)
    # Remove names superseded by the consolidated appendix objects on reruns.
    for stale in ['figure_A1_transition_14.pdf','figure_A1_transition_17.pdf','figure_A3_endpoint_displacement.pdf','figure_A3_endpoint_displacement.png','figure_A3_endpoint_displacement_source.csv','table_A2_displacement_granularity.csv','table_A2_displacement_granularity.tex','table_A2_panel_A_full.csv','table_A2_panel_A_full.tex','table_A2_panel_B_common.csv','table_A2_panel_B_common.tex','table_A2_panel_C_30industry.csv','table_A2_panel_C_30industry.tex','table_A3_method_diagnostics.csv','table_A3_method_diagnostics.tex','table_A4_bootstrap_audit.csv','table_A4_bootstrap_audit.tex','table_A1_panel_A_specification_sensitivity.tex','table_A1_panel_B_materiality_thresholds.tex','table_A2_panel_A_common_origin.tex','table_A2_panel_B_30industry.tex','table_A3_panel_A_us_industries.tex','table_A3_panel_B_countries.tex','table_A4_panel_A_endpoint_inference.tex','table_A4_panel_B_country_secondary.tex','table_A4_panel_C_primary_displacement_intervals.tex','table_A5_panel_A_methods.tex','table_A5_panel_B_data.tex']:
        (O/stale).unlink(missing_ok=True)
    p=json.loads((R/'primary_17_definitive_B2000/summary.json').read_text()); pi=json.loads((R/'primary_17_definitive_B2000/outer_bootstrap_intervals.json').read_text()); c=json.loads((C/'summary.json').read_text()); ci=json.loads((C/'outer_bootstrap_intervals.json').read_text())
    t1=pd.DataFrame([['Endpoint pairs',84,36],['Mean endpoint loss (bp)',f'{bp(p["mean_endpoint_loss"]):.2f}',f'{bp(c["mean_endpoint_loss"]):.2f}'],['95% bootstrap CI (bp)',f'[{bp(pi["baseline_mean_endpoint_loss"][0]):.2f}, {bp(pi["baseline_mean_endpoint_loss"][1]):.2f}]',f'[{bp(ci["mean_endpoint_loss"][0]):.2f}, {bp(ci["mean_endpoint_loss"][1]):.2f}]'],['Median (bp)','0.00','0.00'],['P75 (bp)',f'{bp(p["p75_endpoint_loss"]):.2f}',f'{bp(c["p75_endpoint_loss"]):.2f}'],['P90 (bp)',f'{bp(p["p90_endpoint_loss"]):.2f}',f'{bp(c["p90_endpoint_loss"]):.2f}'],['Literal switching',f'{pct(p["literal_switch_frequency"]):.1f}%',f'{pct(c["literal_switch_frequency"]):.1f}%']],columns=['Metric','17 U.S. industries','14 developed-country markets'])
    t1.to_csv(O/'table_1.csv',index=False); tex(t1,O/'table_1.tex','Endpoint reproducibility','tab:endpoint','lcc')
    math_ci=lambda a,b: f'$[{bp(a):.2f},\\,{bp(b):.2f}]$'
    math_num=lambda x: f'${bp(x):+.2f}$'
    t2=pd.DataFrame([['Decision dates',75,27],['Selector hit rate',f'{pct(p["selector_hit_rate"]):.1f}%',f'{pct(c["selector_hit_rate"]):.1f}%'],['Selection regret (bp)',math_num(p['mean_selection_regret']),math_num(c['mean_selection_regret'])],[r'\quad 95% CI',math_ci(*pi['baseline_mean_selection_regret']),math_ci(*ci['mean_selection_regret'])],['Selector minus ensemble (bp)',math_num(p['mean_selector_minus_ensemble']),math_num(c['mean_selector_minus_ensemble'])],[r'\quad 95% CI',math_ci(*pi['baseline_mean_selector_minus_ensemble']),math_ci(*ci['mean_selector_minus_ensemble'])]],columns=['Metric','17 U.S. industries','14 developed-country markets'])
    t2.to_csv(O/'table_2.csv',index=False); tex(t2,O/'table_2.tex','Ex-ante recoverability','tab:recoverability','lcc')
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
    sens_by=sens.set_index('setting')
    def sens_row(key,label):
        z=sens_by.loc[key]; return [label,f'{10000*z.mean_endpoint_loss:.2f}',f'{100*z.literal_switch_frequency:.1f}%',int(z.median_survival_months_full_km)]
    baseline=['Baseline: L=60 months',f'{bp(p["mean_endpoint_loss"]):.2f}',f'{pct(p["literal_switch_frequency"]):.1f}%',int(p['median_survival_months'])]
    a1a=pd.DataFrame([sens_row('L=36','L=36 months'),baseline,sens_row('L=120','L=120 months'),sens_row('Quarterly','Quarterly rebalancing'),sens_row('gamma2',r'$\gamma=2$'),[r'Baseline: $\gamma=5$',f'{bp(p["mean_endpoint_loss"]):.2f}',f'{pct(p["literal_switch_frequency"]):.1f}%',int(p['median_survival_months'])],sens_row('gamma10',r'$\gamma=10$'),sens_row('cost0','c=0 bp'),['Baseline: c=25 bp',f'{bp(p["mean_endpoint_loss"]):.2f}',f'{pct(p["literal_switch_frequency"]):.1f}%',int(p['median_survival_months'])],sens_row('cost50','c=50 bp')],columns=['Setting','Mean endpoint loss (bp)','Literal switching','Median literal survival (months)'])
    a1b=mat[['universe','threshold_bp','survival_12_complete_followup','survival_24_complete_followup','median_survival_months_full_km']].copy(); a1b['universe']=a1b['universe'].replace({'primary17':'17 U.S. industries','countries':'14 developed-country markets'}); a1b['survival_12_complete_followup']=a1b['survival_12_complete_followup'].map(lambda x:f'{100*x:.1f}%'); a1b['survival_24_complete_followup']=a1b['survival_24_complete_followup'].map(lambda x:f'{100*x:.1f}%'); a1b['median_survival_months_full_km']=a1b['median_survival_months_full_km'].astype(int)
    a1b.columns=['Universe',r'Threshold $\delta$ (bp)',r'$S(12)$',r'$S(24)$','Median (months)']
    a1a.to_csv(O/'table_A1_panel_A_specification_sensitivity.csv',index=False); a1b.to_csv(O/'table_A1_panel_B_materiality_thresholds.csv',index=False)
    a1a_tex=tabular(a1a).replace('\\midrule\n','\\midrule\n\\multicolumn{4}{l}{\\textit{Estimation and rebalancing}} \\\\\n',1).replace('$\\gamma=2$ &','\\multicolumn{4}{l}{\\textit{Risk aversion}} \\\\\n$\\gamma=2$ &').replace('c=0 bp &','\\multicolumn{4}{l}{\\textit{Transaction costs}} \\\\\nc=0 bp &')
    parent_table(O/'table_A1.tex','Robustness to specification choices','tab:robustness',[('Panel A. Implementation and preference sensitivity',a1a_tex),('Panel B. Economic-materiality threshold',tabular(a1b))])
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
        g=g.sort_values('h (months)'); ax.plot(g['h (months)'],g['Mean loss (bp)'],marker='o',linewidth=2,color=colors[universe],label=universe)
    ax.set(xlabel='Endpoint displacement (months)',ylabel='Mean endpoint loss (CEQ bp)',xticks=[6,12,24])
    ax.legend(frameon=False,loc='upper left')
    fig.savefig(O/'figure_2_endpoint_displacement.pdf'); fig.savefig(O/'figure_2_endpoint_displacement.png',dpi=220); plt.close(fig)
    figure2.to_csv(O/'figure_2_endpoint_displacement_source.csv',index=False)
    # Retain the paired primary horizon intervals as an inference table, not
    # unequal visual ornamentation on the two-universe descriptive profile.
    primary_draws=pd.read_csv(R/'primary_17_definitive_B2000/outer_bootstrap.csv')
    primary_columns={6:'h6_mean_endpoint_loss',12:'baseline_mean_endpoint_loss',24:'h24_mean_endpoint_loss'}
    primary_intervals={h:(10000*primary_draws[column].quantile(.025),10000*primary_draws[column].quantile(.975)) for h,column in primary_columns.items()}
    q_common=disp.loc[disp.Sample=='common_calendar_origins'].drop(columns='Sample').copy(); q_common['Universe']=q_common['Universe']+' (n='+q_common['n'].astype(int).astype(str)+')'; q_common=q_common.drop(columns='n'); q_common[['Switching (%)','Loss >25 bp (%)']]=q_common[['Switching (%)','Loss >25 bp (%)']].map(lambda x:f'{x:.1f}%'); q_common.columns=['Universe','h (months)','Mean loss (bp)','P90 (bp)','Switching','Loss >25 bp']; q_common.loc[q_common.duplicated('Universe'),'Universe']=''; q_common.to_csv(O/'table_A2_panel_A_common_origin.csv',index=False)
    s30=json.loads((R/'replication_30_B1000/summary.json').read_text()); i30=json.loads((R/'replication_30_B1000/outer_bootstrap_intervals.json').read_text()); q30=pd.DataFrame([['30 U.S. industries',f'{bp(s30["mean_endpoint_loss"]):.2f}',f'[{bp(i30["mean_endpoint_loss"][0]):.2f}, {bp(i30["mean_endpoint_loss"][1]):.2f}]',f'{pct(s30["literal_switch_frequency"]):.1f}%',s30['median_survival_months']]])
    q30.columns=['Universe','Mean loss (bp)','95% CI (bp)','Switching','Literal median (months)']; q30['Literal median (months)']=q30['Literal median (months)'].astype(int); q30.to_csv(O/'table_A2_panel_B_30industry.csv',index=False)
    parent_table(O/'table_A2.tex','Additional robustness across horizons and universes','tab:additional-robustness',[('Panel A. Common-origin endpoint-displacement robustness',tabular(q_common)),('Panel B. 30-industry granularity check',tabular(q30))])
    labels={'equal_weight':'Equal weight','sample_gmv':'Sample GMV','ledoit_wolf_gmv':'Ledoit--Wolf GMV','inverse_volatility':'Inverse volatility','erc':'ERC'}; frames=[]
    for u,file in [('17 U.S. industries','primary17_winner_conditioned.csv'),('14 developed-country markets','countries_winner_conditioned.csv')]:
        q=pd.read_csv(E/file).set_index('original_winner').reindex(labels).reset_index(); q['universe']=u; frames.append(q)
    a3=pd.concat(frames); a3['original_winner']=a3.original_winner.map(labels); a3['switches']=a3.apply(lambda x: f"{round(x.switch_frequency*x.n_origins):.0f}/{x.n_origins:.0f}" if pd.notna(x.n_origins) else '--',axis=1); a3['material_events']=a3.apply(lambda x: f"{round(x.loss_exceeds_25bp*x.n_origins):.0f}/{x.n_origins:.0f}" if pd.notna(x.n_origins) else '--',axis=1); a3['mean_loss_publication']=a3.apply(lambda x:f'{10000*x.mean_endpoint_loss:.2f}' if pd.notna(x.n_origins) and x.n_origins>=5 else '--',axis=1)
    a3['n_origins']=a3['n_origins'].map(lambda x:str(int(x)) if pd.notna(x) else '--'); a3=a3[['original_winner','n_origins','switches','mean_loss_publication','material_events','universe']].fillna('--')
    a3.columns=['Initial winner','Origins','Switches','Mean endpoint loss (bp)','Loss >25 bp','Universe']
    a3.to_csv(O/'source_A3_method_diagnostics_all.csv',index=False)
    a3_us=a3.loc[a3['Universe']=='17 U.S. industries'].drop(columns='Universe'); a3_country=a3.loc[a3['Universe']=='14 developed-country markets'].drop(columns='Universe')
    parent_table(O/'table_A3.tex','Method-conditioned diagnostics. Conditional mean endpoint loss is suppressed when fewer than five eligible origins are available; event counts remain reported.','tab:methods',[('Panel A. 17 U.S. industries',tabular(a3_us)),('Panel B. 14 developed-country markets',tabular(a3_country))])
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
    a4a['Bootstrap design']=a4a['Bootstrap design'].replace({'Stationary bootstrap':'Stationary','Fixed circular blocks (12 months)':'Circular block, 12m','Fixed circular blocks (24 months)':'Circular block, 24m'})
    a4a.to_csv(O/'table_A4_panel_A_endpoint_inference.csv',index=False)
    a4b=pd.read_csv(E/'country_bootstrap_B1000_summary.csv')[['metric','point_estimate','ci_low','ci_high','unit','bootstrap_replications']].copy()
    a4b['Estimate']=a4b.apply(lambda x:f"{x.point_estimate:.1f}%" if x.unit=='%' else f"{x.point_estimate:.2f}",axis=1); a4b['95% CI']=a4b.apply(lambda x:f"[{x.ci_low:.1f}%, {x.ci_high:.1f}%]" if x.unit=='%' else f"[{x.ci_low:.2f}, {x.ci_high:.2f}]",axis=1)
    a4b['metric']=a4b.apply(lambda x:f"{x.metric} (%)" if x.unit=='%' else x.metric,axis=1); a4b=a4b[['metric','Estimate','95% CI']]; a4b.columns=['Country statistic','Estimate','95% CI']
    a4b.to_csv(O/'table_A4_panel_B_country_secondary.csv',index=False)
    a4c=pd.DataFrame([[h,figure2.loc[(figure2['Universe']=='17 U.S. industries') & (figure2['h (months)']==h),'Mean loss (bp)'].iloc[0],f'[{low:.2f}, {high:.2f}]'] for h,(low,high) in primary_intervals.items()],columns=['Displacement (months)','Endpoint loss (CEQ bp)','95% CI (bp)']).round(2)
    a4c.to_csv(O/'table_A4_panel_C_primary_displacement_intervals.csv',index=False)
    parent_table(O/'table_A4.tex','Bootstrap inference audit','tab:bootstrap',[('Panel A. Endpoint-loss inference',tabular(a4a)),('Panel B. Primary-universe endpoint-displacement inference',tabular(a4c)),('Panel C. Country secondary outcomes (all intervals use B=1,000 stationary-bootstrap replications)',tabular(a4b))])
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
    methods=pd.DataFrame([['Equal weight','None',r'$w_i=1/N$'],['Sample GMV','Sample covariance','Long-only minimum variance'],['Ledoit--Wolf GMV','Shrinkage covariance','Long-only minimum variance'],['Inverse volatility','Sample volatility',r'$w_i\propto1/\hat\sigma_i$'],['ERC','Sample covariance','Equal risk contributions']],columns=['Method','Risk input','Allocation rule'])
    datasets=pd.DataFrame([['17 U.S. industries (N=17)','Kenneth French Data Library','1926-07--2026-07','1931-07',84,75],['14 developed-country markets (N=14)','Kenneth French international','1975-01--2025-12','1980-01',36,27],['30 U.S. industries (N=30)','Kenneth French Data Library','1926-07--2026-07','1931-07',84,75]],columns=['Universe','Source','Sample','OOS start','Endpoint pairs','Ex-ante dates'])
    methods.to_csv(O/'table_A5_panel_A_methods.csv',index=False); datasets.to_csv(O/'table_A5_panel_B_data.csv',index=False)
    parent_table(O/'table_A5.tex','Portfolio methods and sample construction. All methods are long-only and fully invested, use a 60-month estimation window, and rebalance monthly. Returns are monthly USD total returns; the country universe satisfies the frozen January-1975 balanced-panel rule.','tab:implementation-data',[('Panel A. Portfolio methods',tabular(methods)),('Panel B. Data and analysis samples',tabular(datasets))])
    (O/'README.md').write_text('# Lean FRL bundle\n\nMain text: Table 1, Figure 1 (censored-KM winner durability), Figure 2 (endpoint-displacement profiles), and Table 2. For the appendix, insert only `table_A1.tex` through `table_A5.tex`: these are the five publication-level floats, with their panels already inlined. CSV files remain as reproducibility sources. Appendix Table A4 includes the primary h=6/12/24 bootstrap intervals.\n',encoding='utf8')
    (O/'FIGURE_NOTES.md').write_text('# Figure captions and notes\n\n## Figure 1. Winner durability\n\nKaplan--Meier survival of the method identified as winner at each December origin. Literal failure occurs at the first subsequent monthly endpoint at which the original winner loses first place; material failure occurs when its CEQ shortfall first exceeds 25 annualized bp. Recovery of first place does not reset failure.\n\n## Figure 2. Endpoint-displacement profile\n\nMean endpoint loss at the prespecified 6-, 12-, and 24-month endpoint displacements, using the mechanically eligible sample at each displacement. Lines connect reported horizons for visual guidance only; no functional form or monotonic relationship is estimated.\n\n## Figure A1. Winner transitions\n\nRows are conditioned on the method winning at the initial endpoint. Sparse rows are descriptive; in the country universe, inverse volatility and ERC each occur as the initial winner once.\n\n## Figure A2. Leave-one-out sensitivity of mean endpoint loss\n\nEach point is the change in mean 12-month endpoint loss after excluding the indicated asset relative to the corresponding full-universe estimate. The dashed line denotes no change. Asset omission changes both the opportunity set and its dimension, so differences are sensitivity diagnostics rather than asset-specific causal contributions.\n',encoding='utf8')
if __name__=='__main__': main()
