import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr, spearmanr

from .lemon_respiration_eda import EXPECTED, TARGET_HZ, TR

BLUE = '#24658e'
ORANGE = '#a44620'
TEAL = '#24658e'
GRAY = '#d3dce4'


def figures(combined, coverage, windows, traces, out, recording_plots=False):
    plt.rcParams.update({'font.size': 10, 'legend.frameon': False})
    have = combined[combined.respiration_available].copy()
    have['status'] = np.select([have.candidate_657_starts.eq(0),have.candidate_657_starts.eq(1)],
                               ['No full window','One start'],default='Multiple starts')
    def save(fig, name):
        fig.savefig(out/(name+'.png'),dpi=160)
        plt.close(fig)

    fig, axes = plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ax, var, title in zip(axes,('age_group','sex'),('By age group','By recorded gender')):
        block = coverage.query('variable == @var')
        x = 100*block.coverage
        ax.errorbar(x,np.arange(len(block)),xerr=[np.maximum(0, x-100*block.wilson_low),np.maximum(0, 100*block.wilson_high-x)],
                    color=BLUE,fmt='o',capsize=4)
        ax.set(yticks=np.arange(len(block)),yticklabels=[f'{row.group} ({row.respiration_n}/{row.n})' for row in block.itertuples()],
               xlim=(0,100),xlabel='Candidates with respiration (%)',title=title)
        ax.axvline(100 * combined.loc[combined.psq_bold_ecg_candidate, 'respiration_available'].mean(),
                   color=GRAY, ls='--')
    fig.suptitle('Respiration coverage by candidate group (95% Wilson intervals)',fontweight='bold')
    save(fig,'respiration_coverage')

    fig, axes = plt.subplots(1,3,figsize=(13,4.3),layout='constrained')
    for name,color in [('One start',BLUE),('Multiple starts',ORANGE),('No full window',GRAY)]:
        sub=have[have.status==name]
        axes[0].scatter(sub.duration_s/60,sub.triggers,color=color,alpha=.70,s=20,label=f'{name} (n={len(sub)})')
    axes[0].axhline(EXPECTED,color='black',ls=':')
    axes[0].set(xlabel='Recording duration (min)',ylabel='Rising edges')
    axes[0].legend(fontsize=8)
    order=['No full window','One start','Multiple starts']
    colors=[GRAY,BLUE,ORANGE]
    counts=[int((have.status==status).sum()) for status in order]
    axes[1].barh(order,counts,color=colors)
    axes[1].bar_label(axes[1].containers[0],padding=5)
    axes[1].set(xlim=(0,max(counts)*1.17),xlabel='Recordings',title='Windows of 657 consecutive triggers')
    values=np.sort(have.loc[have.status=='Multiple starts','possible_start_span_s'])
    if len(values):
        axes[2].step(values,np.arange(1,len(values)+1)/len(values),where='post',color=ORANGE)
    axes[2].set(xlabel='Time between first and last possible starts (s)',ylabel='Cumulative proportion',
                title='Recordings with multiple starts')
    fig.suptitle('fMRI trigger timing',fontweight='bold')
    save(fig,'respiration_trigger_timing')

    fig, axes = plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
    labels=['Timing','Flat segment ≥0.5 s','Repeated extrema','Low respiratory band power','Rate estimate sensitivity','Irregular intervals']
    flags=['flag_timing','flag_flat','flag_extrema','flag_weak_band','flag_rate_disagreement','flag_irregular_cycles']
    counts=[int(have[c].sum()) for c in flags]
    subcounts=[int(have.loc[have.psq_bold_ecg_candidate,c].sum()) for c in flags]
    y=np.arange(len(flags))
    axes[0].barh(y,counts,color='#aec6cf',label='All recordings')
    axes[0].barh(y,subcounts,color=BLUE,label='ECG–PSQ–fMRI candidates')
    for i,count in enumerate(counts):
        axes[0].text(count+1,i,str(count),va='center',fontsize=9)
    axes[0].set(yticks=y,yticklabels=labels,xlim=(0,max(counts)+20),xlabel='Flagged recordings')
    axes[0].invert_yaxis()
    axes[0].legend(fontsize=8)
    axes[1].scatter(100*have.band_power_fraction,have.method_abs_difference_bpm,
                    c=np.where(have.flag_rate_disagreement,ORANGE,BLUE),alpha=.7,s=19)
    axes[1].axvline(50,color=GRAY,ls='--')
    axes[1].axhline(3,color=GRAY,ls='--')
    axes[1].set(xlabel='Power in the respiratory band (%)',ylabel='Absolute rate difference (breaths/min)')
    fig.suptitle('Respiration quality flags',fontweight='bold')
    save(fig,'respiration_quality')

    fig, axes = plt.subplots(1,3,figsize=(14,4.4),layout='constrained')
    bins=np.arange(5.5,36.6,1.25)
    axes[0].hist(have.spectrum_bpm,bins=bins,histtype='step',linewidth=2,color=BLUE,label='Welch')
    axes[0].hist(have.cycle_bpm,bins=bins,histtype='step',linewidth=2,color=ORANGE,label='Peak interval')
    axes[0].set(xlabel='Respiration rate (breaths/min)',ylabel='Recordings')
    axes[0].legend()
    axes[1].scatter(have.spectrum_bpm,have.cycle_bpm,color=BLUE,alpha=.58,s=18)
    axes[1].plot([6,36],[6,36],color=GRAY,ls='--')
    axes[1].set(xlim=(6,36),ylim=(6,36),xlabel='Welch (breaths/min)',ylabel='Peak interval (breaths/min)')
    difference=have.cycle_bpm-have.spectrum_bpm
    axes[2].scatter((have.cycle_bpm+have.spectrum_bpm)/2,difference,color=BLUE,alpha=.58,s=18)
    axes[2].axhline(0,color=GRAY,ls='--')
    for q in np.nanquantile(difference,[.025,.5,.975]):
        axes[2].axhline(q,color=ORANGE,lw=.8)
    axes[2].set(xlabel='Mean of the two rates (breaths/min)',ylabel='Peak interval − Welch (breaths/min)')
    fig.suptitle('Respiration rate estimates and agreement',fontweight='bold')
    save(fig,'respiration_rate_agreement')

    ordering=have.sort_values(['spectrum_bpm','participant_id']).participant_id
    matrix=windows.pivot(index='participant_id',columns='midpoint_s',values='spectrum_bpm').reindex(ordering)
    good=matrix.to_numpy()
    fig,axes=plt.subplots(1,2,figsize=(11,6),width_ratios=[2,1],layout='constrained')
    view=axes[0].imshow(good,aspect='auto',interpolation='none',cmap='viridis',vmin=6,vmax=36,
                        extent=[0,good.shape[1],len(good),0])
    axes[0].set(xlabel='Time from recording start (min)',ylabel='Recording (ordered by overall rate)')
    fig.colorbar(view,ax=axes[0],label='Breaths/min')
    axes[1].hist(have.window_bpm_iqr,bins=20,color=TEAL)
    axes[1].set(xlabel='IQR of one minute rates (breaths/min)',ylabel='Recordings')
    fig.suptitle('Within-recording respiration rate variation',fontweight='bold')
    save(fig,'respiration_within_recording')

    typical=have[have.status=='One start'].copy()
    typical['deviation']=(typical.spectrum_bpm-have.spectrum_bpm.median()).abs()+typical.method_abs_difference_bpm
    example_rows=[('Typical recording',typical.nsmallest(1,'deviation').iloc[0] if len(typical) else have.iloc[0]),
                  ('Short recording',have.nsmallest(1,'duration_s').iloc[0]),
                  ('Low band power',have.nsmallest(1,'band_power_fraction').iloc[0]),
                  ('Large method difference',have.nlargest(1,'method_abs_difference_bpm').iloc[0])]
    fig,axes=plt.subplots(4,3,figsize=(13,10),layout='constrained')
    for (label,r), panel in zip(example_rows,axes):
        ds,filtered,edges,f,power,peaks,w=traces[r.participant_id]
        t=np.arange(len(ds))/TARGET_HZ
        x=(t>=60)&(t<90)
        scale=np.ptp(np.percentile(filtered[x],[5,95])) or 1
        panel[0].plot(t[x],filtered[x]/scale,color=BLUE,lw=1.1)
        visible=peaks[x[peaks]]
        panel[0].scatter(t[visible],filtered[visible]/scale,color=ORANGE,s=11)
        panel[0].set(title=label,ylabel='Relative amplitude',xlabel='Time (s)')
        mask=(f>=.025)&(f<=1)
        panel[1].plot(f[mask]*60,power[mask]/max(np.max(power[mask]),np.finfo(float).tiny),color=TEAL)
        panel[1].axvline(r.spectrum_bpm,color=ORANGE,ls='--')
        panel[1].set(xlabel='Frequency (breaths/min)',ylabel='Relative power')
        panel[2].plot(w.midpoint_s/60,w.spectrum_bpm,'o-',ms=3,color=BLUE)
        panel[2].set(ylim=(5,37),xlabel='Time (min)',ylabel='Breaths/min')
    fig.suptitle('Example waveforms, spectra and minute estimates',fontweight='bold')
    save(fig,'respiration_examples')

    fig, axes=plt.subplots(1,3,figsize=(13,4.3),layout='constrained')
    cohort=have[have.psq_bold_ecg_candidate]
    groups=['20–39','55–79']
    for pos, age in enumerate(groups):
        for shift, sex, color in [(-.12,'Women',ORANGE),(.12,'Men',BLUE)]:
            metric=cohort.loc[cohort.age_group.eq(age)&cohort.sex.eq(sex),'spectrum_bpm']
            jitter=np.linspace(-.04,.04,len(metric))
            axes[0].scatter(pos+shift+jitter,metric,alpha=.55,s=15,color=color,
                            label=sex if pos==0 else None)
            axes[0].hlines(metric.median(),pos+shift-.09,pos+shift+.09,color=color,lw=2.5)
    axes[0].set(xticks=[0,1],xticklabels=groups,xlabel='Age group',ylabel='Welch (breaths/min)')
    axes[0].legend(fontsize=8)
    axes[1].scatter(have.all_window_median_bpm,have.first_8min_window_median_bpm,color=BLUE,alpha=.6,s=17)
    axes[1].plot([6,36],[6,36],color=GRAY,ls='--')
    axes[1].set(xlabel='All windows, median (breaths/min)',
                ylabel='First 8 windows, median (breaths/min)')
    axes[2].scatter(have.raw_robust_range,have.band_power_fraction*100,alpha=.65,color=TEAL,s=19)
    axes[2].set(xscale='log',xlabel='Raw amplitude P99 − P1 (device units)',ylabel='Power in the respiratory band (%)')
    axes[2].axhline(50,color=GRAY,ls='--')
    fig.suptitle('Respiration rate by group and sensitivity checks',fontweight='bold')
    save(fig,'respiration_sensitivity')

    plot_correlations(have, out)

    if recording_plots:
        plot_recordings(have, traces, out / 'recording_qc')


def plot_correlations(recordings, out):
    """Compare paired estimates and scanner timing across complete pairs."""
    comparisons = [
        ('A  Breathing-rate methods', 'spectrum_bpm', 'cycle_bpm',
         'Welch estimate (breaths/min)', 'Peak-interval estimate (breaths/min)', True),
        ('B  Recording-length sensitivity', 'first_8min_window_median_bpm',
         'all_window_median_bpm', 'First 8 minutes (breaths/min)',
         'Full recording (breaths/min)', True),
        ('C  Scanner trigger timing', 'duration_s', 'triggers',
         'Recording duration (min)', 'Scanner triggers', False),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), layout='constrained')
    for ax, (title, x_col, y_col, xlabel, ylabel, equal_units) in zip(axes, comparisons):
        x, y = recordings[[x_col, y_col]].to_numpy(dtype=float).T
        valid = np.isfinite(x) & np.isfinite(y)
        x, y = x[valid], y[valid]
        if equal_units and x.size:
            lower, upper = min(x.min(), y.min()) - 1, max(x.max(), y.max()) + 1
            ax.plot([lower, upper], [lower, upper], '--', color=GRAY, lw=1.4)
            ax.set(xlim=(lower, upper), ylim=(lower, upper), aspect='equal')
        if x_col == 'duration_s':
            x = x / 60
        ax.scatter(x, y, s=24, alpha=.68, color=BLUE, edgecolors='white', linewidths=.35)
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.grid(alpha=.2)
        if len(x) > 1 and np.ptp(x) > 0 and np.ptp(y) > 0:
            r = pearsonr(x, y).statistic
            rho = spearmanr(x, y).statistic
            precision = 3 if equal_units else 5
            summary = f'Pearson r = {r:.{precision}f}\nSpearman ρ = {rho:.3f}'
        else:
            summary = 'Correlation unavailable'
        ax.text(.04, .96, f'{summary}\nn = {len(x)}', transform=ax.transAxes,
                va='top', bbox=dict(facecolor='white', edgecolor=GRAY, boxstyle='round'))
    fig.suptitle('LEMON respiration correlations', fontweight='bold')
    fig.supxlabel('Dashed lines indicate equal estimates. The full recording includes the first 8 minutes.',
                 fontsize=10)
    fig.savefig(out / 'respiration_correlations.png', dpi=260)
    plt.close(fig)



def plot_recordings(rows, traces, directory):
    directory.mkdir(exist_ok=True)
    for row in rows.itertuples():
        pid = row.participant_id
        raw, filtered, edges, _, _, peaks, _ = traces[pid]
        fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
        fig.subplots_adjust(left=.08, right=.97, bottom=.18, top=.77, wspace=.44)
        bins = np.arange(0, len(raw), 5 * TARGET_HZ)
        minutes = bins / TARGET_HZ / 60
        low = [np.min(raw[b:b + 5 * TARGET_HZ]) for b in bins]
        high = [np.max(raw[b:b + 5 * TARGET_HZ]) for b in bins]
        axes[0].fill_between(minutes, low, high, color=BLUE)
        axes[0].set(title='Signal envelope', xlabel='Time (min)', ylabel='Device units')
        t = np.arange(60 * TARGET_HZ, 90 * TARGET_HZ)
        visible = peaks[(peaks >= t[0]) & (peaks <= t[-1])]
        axes[1].plot(t / TARGET_HZ, filtered[t], color=BLUE)
        axes[1].scatter(visible / TARGET_HZ, filtered[visible], color=ORANGE, s=9)
        axes[1].set(title='Filtered sample', xlabel='Time (s)')
        axes[2].scatter(edges[1:] / 60, 1000 * (np.diff(edges) - TR), s=3, color=BLUE)
        axes[2].set(title=f'{int(row.triggers)} edges, {int(row.candidate_657_starts)} starts',
                    xlabel='Time (min)', ylabel='Deviation from 1.4 s (ms)', ylim=(-1, 1))
        fig.suptitle(f'{pid}: Welch rate {row.spectrum_bpm:.1f} breaths/min')
        fig.savefig(directory / f'{pid}.png', dpi=120)
        plt.close(fig)
