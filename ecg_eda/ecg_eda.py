"""Portable local-file ECG EDA. No downloads, HRV validation or model fitting.

Read LEMON ses-01 ECG TSV(.gz) with its JSON sidecar, save file-level metrics,
review flags and individual QC plots. Preserve original signals on disk.
"""
import argparse, csv, gzip, json, os, re, tempfile
from pathlib import Path
from collections import Counter
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'ecg-eda-mpl'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import neurokit2 as nk


def longest(mask):
    changes = np.diff(np.r_[False, mask, False].astype(np.int8))
    starts, ends = np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)
    return int(np.max(ends-starts)) if len(starts) else 0


def inspect(path, output):
    """Return metrics and exploratory review prompts for one full recording."""
    stem = path.name.removesuffix('.gz').removesuffix('.tsv')
    sidecar = path.with_name(stem+'.json')
    pid = re.search(r'sub-\d+', path.name).group()
    row = {'participant_id':pid, 'source_file':path.name, 'status':'error', 'validated_hrv':False}
    try:
        meta = json.loads(sidecar.read_text())
        fs = float(meta['SamplingFrequency']); cols = meta['Columns']
        if fs <= 0 or 'ecg' not in cols:
            raise ValueError('Invalid sampling frequency or absent ECG column')
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as f:
            data = np.loadtxt(f, ndmin=2)
        if data.shape[1] != len(cols):
            raise ValueError('Data columns do not match JSON metadata')
        x = data[:, cols.index('ecg')]
        finite = np.isfinite(x)
        if not finite.any():
            raise ValueError('No finite ECG samples')
        median = float(np.median(x[finite]))
        mad = float(np.median(np.abs(x[finite]-median)))
        duration = len(x)/fs
        same = (np.diff(x)==0) & np.isfinite(np.diff(x))
        flat_s = (longest(same)+1)/fs if same.any() else 0
        extreme = np.abs(x-median)>20*1.4826*mad if mad>0 else np.zeros(len(x),bool)
        row.update(status='readable', rows=len(x), sampling_hz=fs, channel_count=len(cols),
                   duration_s=duration, nonfinite_n=int((~finite).sum()), ecg_mad=mad,
                   longest_constant_run_s=flat_s, longest_extreme_20mad_run_s=longest(extreme)/fs,
                   gzip_crc_checked=path.suffix=='.gz')
        flags=[]
        if not finite.all(): flags.append('nonfinite_samples')
        if flat_s>=1: flags.append('constant_run_ge_1s')
        if longest(extreme)/fs>=1: flags.append('sustained_extreme_amplitude')
        if abs(duration-919.8)>.01: flags.append('duration_not_919p8s')
        if 'trigger' in cols:
            tr=data[:,cols.index('trigger')]
            rises=np.flatnonzero(np.diff(np.r_[False,tr>0].astype(np.int8))==1)
            gaps=np.diff(rises)/fs
            row['trigger_count']=len(rises)
            row['trigger_median_spacing_s']=float(np.median(gaps)) if len(gaps) else None
            if len(rises)!=657: flags.append('trigger_count_not_657')
            if not len(gaps) or abs(np.median(gaps)-1.4)>.005: flags.append('trigger_spacing_check')
        peaks=np.array([],int); first=np.array([],int)
        row['detection_status']='not_run'
        if finite.all() and mad>0 and duration>=60:
            try:
                cleaned=nk.ecg_clean(x,sampling_rate=fs,method='neurokit')
                _, info=nk.ecg_peaks(cleaned,sampling_rate=fs,method='neurokit',correct_artifacts=False)
                peaks=np.asarray(info['ECG_R_Peaks'],int)
                rr=np.diff(peaks)/fs*1000
                counts=[]
                for method in ['neurokit','engzeemod2012']:
                    short=nk.ecg_clean(x[:int(60*fs)],sampling_rate=fs,method=method)
                    _, info=nk.ecg_peaks(short,sampling_rate=fs,method=method,correct_artifacts=False)
                    found=np.asarray(info['ECG_R_Peaks'],int); counts.append(len(found))
                    if method=='neurokit': first=found
                row.update(detection_status='completed_unvalidated',first60_neurokit_n=counts[0],first60_engzee_n=counts[1],full_candidate_n=len(peaks))
                if not all(counts): flags.append('detector_empty_first60')
                if len(rr):
                    row['candidate_median_interval_ms']=float(np.median(rr))
                    if ((rr<300)|(rr>2000)).any(): flags.append('candidate_interval_outside_300_2000ms')
                    if len(rr)>1 and ((rr[1:]/rr[:-1]<.5)|(rr[1:]/rr[:-1]>2)).any(): flags.append('abrupt_candidate_interval_ratio')
            except Exception as exc:
                row['detection_status']='error';row['detection_error']=str(exc)
                flags.append('detection_error')
        row['review_flags']='; '.join(flags)
        # A full overview plus a short raw window; candidates remain unvalidated.
        fig,axes=plt.subplots(2,1,figsize=(12,6),layout='constrained')
        step=max(1,len(x)//20000)
        axes[0].plot(np.arange(0,len(x),step)/fs,x[::step],lw=.4)
        axes[0].set(title=pid+' raw ECG overview',xlabel='Time (s)',ylabel='Stored amplitude')
        n=min(len(x),int(10*fs)); visible=first[first<n]
        axes[1].plot(np.arange(n)/fs,x[:n],lw=.6)
        axes[1].scatter(visible/fs,x[visible],s=12,c='red',label='Unvalidated candidates')
        axes[1].set(xlabel='Time (s)',ylabel='Stored amplitude',title='First 10 seconds')
        if len(visible):axes[1].legend()
        fig.savefig(output/'private'/'qc_figures'/(pid+'.png'),dpi=150);plt.close(fig)
    except Exception as exc:
        row['error']=str(exc)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True,help='Local ECG TSV(.gz) files with JSON sidecars')
    parser.add_argument('--output',type=Path,default=Path('ecg_results'))
    parser.add_argument('--subjects',type=Path,help='Optional CSV with ID or participant_id column')
    args=parser.parse_args(); output=args.output.resolve()
    (output/'private'/'qc_figures').mkdir(parents=True,exist_ok=True)
    (output/'.gitignore').write_text('private/\n')
    files=sorted(p for p in args.data_dir.rglob('*recording-ecg_physio.tsv*')
                 if re.search(r'sub-\d+_ses-01_task-rest_acq-AP_run-01_recording-ecg_physio\.tsv(\.gz)?$',p.name))
    if args.subjects:
        with args.subjects.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        key='ID' if rows and 'ID' in rows[0] else 'participant_id'
        ids=[r[key].strip() for r in rows]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate IDs in subject list')
        files=[p for p in files if re.search(r'sub-\d+',p.name).group() in set(ids)]
    names=[re.search(r'sub-\d+',p.name).group() for p in files]
    if len(set(names))!=len(names):raise ValueError('Duplicate participant recordings; keep one input per participant')
    if not files:raise ValueError('No matching main-session ECG files found')
    results=[]
    for i,path in enumerate(files,1):
        row=inspect(path,output);results.append(row);print(f'{i}/{len(files)} {row["participant_id"]}: {row["status"]}',flush=True)
    keys=sorted(set().union(*(r.keys() for r in results)))
    with (output/'private'/'participant_eda.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(results)
    good=[r for r in results if r['status']=='readable']
    summary={'files_processed':len(results),'readable_n':len(good),'validated_hrv_computed':False,
             'final_usable_n':None,'neurokit_version':nk.__version__,
             'flags_are':'Exploratory review prompts, not exclusion decisions',
             'flag_counts':dict(Counter(flag for r in good for flag in r.get('review_flags','').split('; ') if flag))}
    (output/'aggregate_summary.json').write_text(json.dumps(summary,indent=2))
    if good:
        fig,ax=plt.subplots(1,2,figsize=(10,4),layout='constrained')
        duration=np.sort([r['duration_s'] for r in good])
        ax[0].step(duration,np.arange(1,len(duration)+1)/len(duration),where='post')
        ax[0].set(xlabel='Duration (s)',ylabel='Cumulative proportion',title='Recording duration')
        mad=np.array([r['ecg_mad'] for r in good]);mad=mad[mad>0]
        if len(mad):ax[1].boxplot(mad);ax[1].scatter(np.ones(len(mad)),mad,s=12,alpha=.4);ax[1].set_yscale('log')
        ax[1].set(ylabel='Amplitude MAD (stored units)',title='Signal amplitude variability')
        fig.savefig(output/'ecg_duration_and_mad.png',dpi=250);plt.close(fig)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
