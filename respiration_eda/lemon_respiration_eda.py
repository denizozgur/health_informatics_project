from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import json
import re

import numpy as np
import pandas as pd
from scipy import signal

TR = 1.4
EXPECTED = 657
EDGE_TOLERANCE = 0.05
TARGET_HZ = 20
BAND = (0.10, 0.60)
WINDOW = 60
WINDOW_METRICS = ('spectrum_bpm', 'band_power_fraction', 'spectral_concentration')
WINDOW_COLUMNS = ('participant_id', 'start_s', 'end_s', 'midpoint_s', *WINDOW_METRICS)


def longest_run(mask):
    boundaries = np.flatnonzero(np.diff(np.r_[False, mask, False]))
    return np.diff(boundaries.reshape(-1, 2), axis=1).max(initial=0)


def spectrum(x, seconds):
    if np.ptp(x) == 0:
        x = np.zeros_like(x)
    f, power = signal.welch(x, fs=TARGET_HZ, nperseg=min(len(x), seconds * TARGET_HZ))
    band = (f >= BAND[0]) & (f <= BAND[1])
    total = (f >= 0.02) & (f <= 5)
    if not band.any() or not power[total].sum() > 0:
        return np.nan, np.nan, np.nan, f, power
    band_f, band_power = f[band], power[band]
    peak = np.argmax(band_power)
    frequency = band_f[peak]
    if 0 < peak < len(band_f) - 1:
        a, b, c = np.log(np.maximum(band_power[peak-1:peak+2], np.finfo(float).tiny))
        if a - 2*b + c < 0:
            frequency += (f[1] - f[0]) * np.clip(0.5 * (a-c) / (a-2*b+c), -0.5, 0.5)
    return 60*frequency, band_power.sum()/power[total].sum(), band_power[abs(band_f-frequency)<=0.04].sum()/band_power.sum(), f, power


def analyze(path):
    pid = path.name.split('_')[0]
    meta = json.loads(path.with_suffix('').with_suffix('.json').read_text())
    frame = pd.read_csv(path, sep='\t', header=None, dtype=float)
    cols = meta['Columns']
    if frame.shape[1] == len(cols)+1 and frame.iloc[:, -1].isna().all():
        frame = frame.iloc[:, :-1]
    assert frame.shape[1] == len(cols) and set(cols) == {'resp','trigger'}, path
    raw = frame.iloc[:, cols.index('resp')].to_numpy()
    trg = frame.iloc[:, cols.index('trigger')].to_numpy()
    hz = int(meta['SamplingFrequency'])
    finite = np.isfinite(raw)
    edges = np.flatnonzero(np.diff(np.r_[False, np.isfinite(trg) & (trg > 0)].astype(np.int8)) == 1) / hz
    intervals = np.diff(edges)
    regular = abs(intervals - TR) <= EDGE_TOLERANCE
    bad_cum = np.r_[0, np.cumsum(~regular)]
    length = EXPECTED - 1
    starts = np.flatnonzero(bad_cum[length:] == bad_cum[:-length]) if len(intervals) >= length else np.array([], dtype=int)
    longest = int(longest_run(regular)) + int(bool(edges.size))
    r = {
        'participant_id': pid, 'sampling_hz': hz, 'start_time_json_s': meta['StartTime'], 'samples': len(raw),
        'duration_s': len(raw)/hz, 'nonfinite_resp': int((~finite).sum()), 'nonfinite_trigger': int((~np.isfinite(trg)).sum()),
        'constant_resp': bool(finite.any() and np.ptp(raw[finite]) == 0),
        'flat_longest_s': (int(longest_run(np.diff(raw) == 0)) + 1) / hz,
        'equal_adjacent_pct': 100*np.mean(np.diff(raw) == 0),
        'max_min_occupancy_pct': 100*max(np.mean(raw==np.nanmin(raw)), np.mean(raw==np.nanmax(raw))),
        'triggers': len(edges), 'first_trigger_s': edges[0] if edges.size else np.nan,
        'last_trigger_s': edges[-1] if edges.size else np.nan,
        'median_trigger_interval_s': np.median(intervals) if intervals.size else np.nan,
        'max_trigger_jitter_ms': 1000*np.max(abs(intervals-TR)) if intervals.size else np.nan,
        'trigger_exact_grid_pct': 100*np.mean(abs(intervals-TR)<0.0005) if intervals.size else np.nan,
        'after_last_trigger_s': len(raw)/hz-edges[-1] if edges.size else np.nan,
        'possible_start_span_s': float(edges[starts[-1]]-edges[starts[0]]) if len(starts) else np.nan,
        'regular_trigger_pct': 100*np.mean(regular) if intervals.size else np.nan,
        'longest_regular_train': longest, 'candidate_657_starts': len(starts),
        'unique_start_edge_1based': int(starts[0]+1) if len(starts)==1 else np.nan,
        'unique_first_retained_s': edges[starts[0]+5] if len(starts)==1 else np.nan,
        'unique_last_retained_s': edges[starts[0]+EXPECTED-1] if len(starts)==1 else np.nan,
    }
    good_indices = np.flatnonzero(finite)
    if good_indices.size and not finite.all():
        raw = np.interp(np.arange(len(raw)), good_indices, raw[finite])
    assert hz % TARGET_HZ == 0 and good_indices.size, path
    downsample = hz // TARGET_HZ
    if r['constant_resp']:
        # Avoid edge transients from padding a constant signal with zeros.
        ds = raw[::downsample].copy()
        filtered = np.zeros_like(ds)
    else:
        ds = signal.resample_poly(raw, 1, downsample)
        sos = signal.butter(3, BAND, btype='bandpass', fs=TARGET_HZ, output='sos')
        filtered = signal.sosfiltfilt(sos, ds)
    scale = (np.percentile(filtered, 75) - np.percentile(filtered, 25)) / 1.349
    spec, share, concentration, f, power = spectrum(ds, 120)
    r.update(spectrum_bpm=spec, band_power_fraction=share, spectral_concentration=concentration,
             raw_robust_range=np.percentile(raw, 99)-np.percentile(raw, 1))
    cycles = {}
    for polarity in (1,-1):
        for prominence in (.25,.5,1):
            peaks = signal.find_peaks(polarity*filtered, distance=int(np.ceil(TARGET_HZ/BAND[1])),
                                      prominence=prominence*scale)[0] if scale>0 else np.array([],dtype=int)
            peaks = peaks[(peaks>=5*TARGET_HZ) & (peaks<(len(ds)-5*TARGET_HZ))]
            ibi = np.diff(peaks)/TARGET_HZ
            valid = (ibi>=1/BAND[1]) & (ibi<=1/BAND[0])
            cycles[polarity,prominence] = (60/np.median(ibi[valid]) if valid.any() else np.nan, peaks, ibi, valid)
    bpm, peaks, ibi, valid = cycles[1,.5]
    variants = np.array([v[0] for v in cycles.values()])
    r.update(cycle_bpm=bpm, cycle_detected=len(ibi), cycle_valid=int(valid.sum()),
             cycle_valid_pct=100*valid.mean() if valid.size else np.nan,
             cycle_ibi_iqr_s=np.diff(np.percentile(ibi[valid],[25,75]))[0] if valid.any() else np.nan,
             sensitivity_bpm_span=np.ptp(variants[np.isfinite(variants)]) if np.isfinite(variants).any() else np.nan,
             method_abs_difference_bpm=abs(bpm-spec))
    windows = []
    for i in range(len(ds)//(WINDOW*TARGET_HZ)):
        a, b = i*WINDOW, (i+1)*WINDOW
        sw, bw, cw, *_ = spectrum(ds[a*TARGET_HZ:b*TARGET_HZ], 40)
        windows.append(dict(participant_id=pid, start_s=a, end_s=b, midpoint_s=(a+b)/2,
                            spectrum_bpm=sw, band_power_fraction=bw, spectral_concentration=cw))
    wr = pd.DataFrame(windows, columns=WINDOW_COLUMNS).astype(dict.fromkeys(WINDOW_METRICS, float))
    r.update(windows=len(wr),
             first_8min_window_median_bpm=wr.spectrum_bpm.head(8).median(),
             all_window_median_bpm=wr.spectrum_bpm.median(), weak_band_windows_pct=100*(wr.band_power_fraction<.5).mean(),
             window_bpm_iqr=np.diff(wr.spectrum_bpm.quantile([.25,.75]))[0],
             late_minus_early_bpm=wr.spectrum_bpm.tail(3).median()-wr.spectrum_bpm.head(3).median())
    r.update(flag_timing=len(starts)!=1 or len(edges)<EXPECTED,
             flag_flat=r['flat_longest_s']>=.5, flag_extrema=r['max_min_occupancy_pct']>=1,
             flag_weak_band=not np.isfinite(share) or share<.5 or r['weak_band_windows_pct']>=25,
             flag_rate_disagreement=r['method_abs_difference_bpm']>3 or r['sensitivity_bpm_span']>3 or not np.isfinite(bpm),
             flag_irregular_cycles=not valid.size or valid.mean()<.8)
    plot = (ds, filtered, edges, f, power, peaks, wr)
    return r, windows, plot


def cohort_tables(base, demographics, metrics):
    demo = pd.read_csv(demographics, usecols=['ID','Age','Gender_ 1=female_2=male'])
    demo = demo.rename(columns={'ID':'participant_id','Age':'age_bin','Gender_ 1=female_2=male':'sex_code'})
    demo.participant_id = demo.participant_id.str.strip().str.lower()
    demo = demo[demo.participant_id.str.fullmatch(r'sub-\d{6}', na=False)].drop_duplicates('participant_id',keep=False)
    demo['age_group'] = np.where(demo.age_bin.str.match(r'^[23]\d-',na=False),'20–39',
                                 np.where(demo.age_bin.str.match(r'^[5-7]\d-',na=False),'55–79','Unknown'))
    demo['sex'] = demo.sex_code.map({1:'Women',2:'Men'})
    candidates = pd.read_csv(base, usecols=['ID'], dtype=str).ID.str.strip().str.lower()
    if not candidates.str.fullmatch(r'sub-\d{6}', na=False).all() or not candidates.is_unique:
        raise ValueError('Expected unique LEMON participant IDs in the cohort CSV')
    participants = sorted(set(candidates) | set(metrics.participant_id))
    base = pd.DataFrame({'participant_id': participants})
    base['psq_bold_ecg_candidate'] = base.participant_id.isin(candidates)
    base['respiration_available'] = base.participant_id.isin(metrics.participant_id)
    merged = base.merge(demo.drop(columns='sex_code'), how='left', validate='one_to_one')
    merged = merged.merge(metrics, how='left', validate='one_to_one')
    cohort = merged[merged.psq_bold_ecg_candidate]
    coverage = []
    for column in ('age_group','age_bin','sex'):
        for group, rows in cohort.groupby(column,dropna=False):
            n = len(rows)
            k = int(rows.respiration_available.sum())
            p = k/n
            z = 1.95996398454
            center = (p+z*z/(2*n))/(1+z*z/n)
            half = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
            coverage.append(dict(variable=column, group=group, n=n, respiration_n=k, missing_n=n-k,
                                 coverage=p, wilson_low=max(0,center-half), wilson_high=min(1,center+half)))
    return merged, pd.DataFrame(coverage)


def main():
    parser = argparse.ArgumentParser()
    for arg in ('data','base','demographics','output'):
        parser.add_argument('--' + arg, required=True, type=Path)
    parser.add_argument('--recording-plots', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    paths = sorted(args.data.rglob('*_ses-01_task-rest_acq-AP_run-01_recording-resp_physio.tsv.gz'))
    if not paths or len({p.name.split('_')[0] for p in paths}) != len(paths):
        raise ValueError('Expected one respiration file per participant in session 01, AP, run 01')
    with ThreadPoolExecutor(max_workers=5) as pool:
        result = list(pool.map(analyze, paths))
    rows = pd.DataFrame([r for r,_,_ in result])
    windows = pd.DataFrame([w for _, ws,_ in result for w in ws], columns=WINDOW_COLUMNS)
    combined, coverage = cohort_tables(args.base,args.demographics,rows)
    combined.to_csv(args.output/'participant_eda.csv',index=False)
    coverage.to_csv(args.output/'cohort_coverage.csv',index=False)
    windows.to_csv(args.output/'minute_windows.csv',index=False)
    print(rows.select_dtypes('number').describe().T.to_string(),flush=True)
    print(coverage.to_string(index=False),flush=True)
    print(combined.groupby(['psq_bold_ecg_candidate','respiration_available']).size().to_string(),flush=True)
    print(rows.select_dtypes('bool').sum().to_string(),flush=True)
    from .lemon_respiration_plots import figures

    traces = {row['participant_id']: trace for row, _, trace in result}
    figures(combined, coverage, windows, traces, args.output, args.recording_plots)


if __name__ == '__main__':
    main()
