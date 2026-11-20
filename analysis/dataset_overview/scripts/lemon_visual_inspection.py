"""Inspect bounded MRI and EEG examples; no clinical interpretation or feature training."""

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from scipy.io import loadmat
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[3]
SUBSET = ROOT / "data/lemon/subset"
OUT = ROOT / "data/derived/dataset_overview"


def main():
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    image_records, eeg_records = [], []
    participants = [("sub-010003", "young, age bin 20–25"), ("sub-010002", "older, age bin 65–70")]
    for sequence in ("T1w", "T2w", "FLAIR"):
        fig, axes = plt.subplots(2, 3, figsize=(11, 8), layout="constrained")
        hist, hist_axes = plt.subplots(1, 2, figsize=(10, 3), layout="constrained")
        for row, (participant, description) in enumerate(participants):
            path = next((SUBSET / participant).glob(f"*_{sequence}.nii.gz"))
            original = nib.load(path)
            canonical = nib.as_closest_canonical(original)
            array = canonical.get_fdata(dtype=np.float32)
            spacing = canonical.header.get_zooms()[:3]
            finite = array[np.isfinite(array)]
            display = finite[finite > 0]
            low, high = np.percentile(display, [2, 98])
            record = {"participant": participant, "age_description": description, "sequence": sequence,
                      "file": str(path.relative_to(ROOT)), "shape": list(original.shape),
                      "voxel_spacing_mm": [float(x) for x in original.header.get_zooms()],
                      "orientation": list(nib.aff2axcodes(original.affine)), "affine": original.affine.tolist(),
                      "qform_code": int(original.header['qform_code']), "sform_code": int(original.header['sform_code']),
                      "dtype": str(original.get_data_dtype()), "nonfinite_voxels": int((~np.isfinite(array)).sum()),
                      "intensity_min": float(finite.min()), "intensity_max": float(finite.max()),
                      "display_percentiles_positive_2_98": [float(low), float(high)],
                      "stage": "Raw release, defaced; RAS reorientation for display only"}
            image_records.append(record)
            for col, (axis, title, horizontal, vertical) in enumerate([
                (0, "Sagittal", 1, 2), (1, "Coronal", 0, 2), (2, "Axial", 0, 1)]):
                plane = np.take(array, array.shape[axis] // 2, axis=axis).T
                axes[row, col].imshow(plane, origin="lower", cmap="gray", vmin=low, vmax=high,
                                      aspect=spacing[vertical] / spacing[horizontal])
                axes[row, col].set_title(f"{title} | {description}", fontsize=10)
                axes[row, col].set_xlabel(["Posterior → Anterior", "Left → Right", "Left → Right"][col])
                axes[row, col].set_ylabel(["Inferior → Superior", "Inferior → Superior", "Posterior → Anterior"][col])
                axes[row, col].set_xticks([]); axes[row, col].set_yticks([])
            hist_axes[row].hist(finite[::10], bins=100, color="#327c98", log=True)
            hist_axes[row].set(title=description, xlabel="Stored image intensity (arbitrary units)", ylabel="Voxel count (log)")
        fig.suptitle(f"{sequence} inspection | RAS voxel planes, physical aspect ratio, no registration\nTwo examples only; display contrast adjusted per image")
        fig.savefig(OUT / f"figures/mri_{sequence}_planes.png", dpi=150); plt.close(fig)
        hist.suptitle(f"{sequence} intensity distributions (deterministic every tenth voxel; includes background)")
        hist.savefig(OUT / f"figures/mri_{sequence}_intensities.png", dpi=150); plt.close(hist)
    fig, axes = plt.subplots(2, 2, figsize=(13, 7), layout="constrained")
    for row, (participant, description) in enumerate(participants):
        path = next((SUBSET / participant).glob("*_EO.set"))
        eeg = loadmat(path, simplify_cells=True)["EEG"]
        channels, points, rate = int(eeg['nbchan']), int(eeg['pnts']), float(eeg['srate'])
        signal_path = path.with_name(str(eeg['data']))
        if signal_path.stat().st_size != channels * points * 4:
            raise ValueError(f"EEGLAB data size does not match header: {path.name}")
        signals = np.memmap(signal_path, dtype="<f4", mode="r", shape=(channels, points), order="F")
        events = eeg.get('event', [])
        if isinstance(events, dict): events = [events]
        boundaries = [int(float(event['latency'])) for event in events if str(event.get('type', '')).lower() == 'boundary']
        intervals = list(zip([0] + sorted(boundaries), sorted(boundaries) + [points]))
        start, end = max(intervals, key=lambda interval: interval[1] - interval[0])
        # Skip one sample adjacent to each boundary; use at most 60 s from one continuous interval.
        start += 1
        end = min(end - 1, start + int(60 * rate))
        labels = [channel['labels'] for channel in eeg['chanlocs']]
        selected = [labels.index(name) for name in ('Fp1', 'Cz', 'Oz') if name in labels]
        segment = np.asarray(signals[selected, start:end], dtype=float)
        samples = min(int(5 * rate), segment.shape[1])
        offsets = np.arange(len(selected)) * 50
        for i, channel in enumerate(selected):
            trace = segment[i, :samples] - np.median(segment[i, :samples])
            axes[row, 0].plot(np.arange(samples)/rate, trace + offsets[i], linewidth=.6, label=labels[channel])
        axes[row, 0].set(xlabel="Time within selected continuous interval (s)", ylabel="Amplitude + 50 µV offsets",
                         title=f"{description} | preprocessed EO, {channels} channels, {rate:g} Hz")
        axes[row, 0].legend(fontsize=8)
        frequency, power = welch(segment, fs=rate, nperseg=min(int(4*rate), segment.shape[1]),
                                 noverlap=min(int(2*rate), segment.shape[1]//2), axis=-1)
        keep = (frequency >= 1) & (frequency <= 60)
        for i, channel in enumerate(selected):
            axes[row, 1].semilogy(frequency[keep], power[i, keep], label=labels[channel])
        axes[row, 1].axvspan(45, 60, alpha=.1, color='gray', label="Outside released 1–45 Hz passband")
        axes[row, 1].set(xlabel="Frequency (Hz)", ylabel="PSD (µV²/Hz; EEGLAB unit convention)", title="Welch PSD, one continuous interval ≤60 s")
        axes[row, 1].legend(fontsize=8)
        eeg_records.append({"participant": participant, "stage": "Released ICA-cleaned, eyes open", "channels": channels,
                            "sampling_hz": rate, "samples": points, "duration_seconds": points/rate,
                            "boundary_events": len(boundaries), "psd_interval_sample_start": start,
                            "psd_interval_sample_end": end, "amplitude_units": "µV assumed from EEGLAB convention; no rescaling"})
    fig.suptitle("EEG inspection | Different sessions from MRI; traces are not simultaneous with MRI")
    fig.savefig(OUT / "figures/eeg_preprocessed_signals_psd.png", dpi=150); plt.close(fig)
    header_path = SUBSET / "sub-010002/sub-010002.vhdr"
    raw_path = SUBSET / "sub-010002/sub-010002_first10s.eeg"
    if raw_path.exists():
        header = header_path.read_text()
        channels = int(re.search(r"NumberOfChannels=(\d+)", header)[1])
        rate = 1e6/float(re.search(r"SamplingInterval=(\d+)", header)[1])
        if 'DataOrientation=MULTIPLEXED' not in header or 'BinaryFormat=INT_16' not in header:
            raise ValueError("Unsupported raw EEG encoding")
        raw = np.fromfile(raw_path, dtype='<i2').reshape(-1, channels)
        fig, axes = plt.subplots(2, 1, figsize=(12, 6), layout="constrained")
        for name in ['Fp1','Cz','VEOG','Oz']:
            match = re.search(r'^Ch(\d+)='+name+r',,[^\n]+', header, re.M)
            fields = match[0].split('=')[1].split(',')
            scale = float(fields[2])
            trace = raw[:, int(match[1])-1] * scale
            offset = ['Fp1','Cz','VEOG','Oz'].index(name)*150
            axes[0].plot(np.arange(len(trace))/rate, trace-np.median(trace)+offset, linewidth=.5, label=name)
            f,p=welch(trace,fs=rate,nperseg=int(2*rate))
            mask=(f>=1)&(f<=100)
            axes[1].semilogy(f[mask],p[mask],label=name)
        axes[0].set(xlabel='Time from recording start (s)',ylabel='µV + 150 µV offsets',title='Raw EEG prefix, older example; includes eye channel VEOG')
        axes[1].set(xlabel='Frequency (Hz)',ylabel='PSD (µV²/Hz)',title='Welch PSD of the same 10 s prefix; not directly comparable with cleaned EO interval')
        for ax in axes: ax.legend(fontsize=8)
        fig.savefig(OUT/'figures/eeg_raw_prefix.png',dpi=150);plt.close(fig)
        eeg_records.append({'participant':'sub-010002','stage':'Raw prefix only','channels':channels,'sampling_hz':rate,
                            'samples':len(raw),'duration_seconds':len(raw)/rate,'amplitude_units':'µV; header scale applied'})
    (OUT / "image_characteristics.json").write_text(json.dumps(image_records, indent=2))
    (OUT / "eeg_characteristics.json").write_text(json.dumps(eeg_records, indent=2))
    print(f"Saved inspection figures and metadata for {len(image_records)} images and {len(eeg_records)} signals")


if __name__ == "__main__":
    main()
