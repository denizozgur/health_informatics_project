#!/usr/bin/env python
"""Task 3 EDA, step 3 of 3: independent re-computation of key numbers, straight from the raw files.

    uv run python analysis/fmri_eda/scripts/eda_verify.py            # 2 scans (fast)
    uv run python analysis/fmri_eda/scripts/eda_verify.py --all      # all cached scans (about 1 min each)

Deliberately shares NO code with eda_extract.py / eda_report.py:
  - NIfTI header parsed byte-by-byte with `struct` (no nibabel); voxel data decoded with numpy.frombuffer
  - voxel statistics computed with a two-pass float64 loop over volumes (not the vectorised path)
  - triggers counted with a different edge rule (any sample > 0 that follows a 0 sample)
  - MeanFD recomputed from the raw text file with plain Python arithmetic
Each comparison is written to data/derived/fmri_eda/eda/verify_results.csv as PASS/FAIL.
"""
import gzip
import json
import struct
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
EDA = ROOT / "data/derived/fmri_eda/eda"
EXTRAS = ROOT / "data/LEMON/MRI_extras"
res = []


def record(what, subject, ours, reference, tol):
    ok = abs(float(ours) - float(reference)) <= tol
    res.append(dict(check=what, subject=subject, independent=ours, pipeline_value=reference, tolerance=tol, status="PASS" if ok else "FAIL"))


def read_nifti(path, want_data):
    with gzip.open(path, "rb") as f:
        h = f.read(348)
        dim = struct.unpack("<8h", h[40:56]); pixdim = struct.unpack("<8f", h[76:108])
        vox_offset = struct.unpack("<f", h[108:112])[0]
        srow = [struct.unpack("<4f", h[280 + 16 * k:296 + 16 * k]) for k in range(3)]
        hdr = dict(dim=dim[1:5], pixdim=pixdim[1:5], srow=srow)
        if not want_data:
            return hdr, None
        f.read(int(vox_offset) - 348)
        nx, ny, nz, nt = dim[1:5]
        s1 = np.zeros(nx * ny * nz); s2 = np.zeros(nx * ny * nz); nan = 0
        for _ in range(nt):
            v = np.frombuffer(f.read(nx * ny * nz * 4), "<f4").astype(np.float64)
            nan += int(np.isnan(v).sum()); s1 += v
        mean = s1 / nt
    with gzip.open(path, "rb") as f:          # second pass: variance around the mean
        f.read(int(vox_offset))
        for _ in range(nt):
            v = np.frombuffer(f.read(nx * ny * nz * 4), "<f4").astype(np.float64)
            s2 += (v - mean) ** 2
    std = np.sqrt(s2 / nt)
    return hdr, dict(mean=mean, std=std, nan=nan)


def main():
    nm = pd.read_csv(ROOT / "data/LEMON/name_match.csv"); p2a = dict(zip(nm.Initial_ID, nm.INDI_ID))
    cache = {p.stem: json.loads(p.read_text()) for p in (EDA / "cache").glob("sub-*.json")}
    raw = ROOT / "data/LEMON/MRI_MNI2mm"
    local = [s for s in sorted(cache) if (raw / f"{s}_ses-01_task-rest_acq-AP_run-01_MNI2mm.nii.gz").exists()]
    subs = local if "--all" in sys.argv else local[:2]          # raw-scan checks need the scan on this laptop

    # --- TR from bold.json sidecars (plain json, no pandas)
    trs = [json.load(open(p))["RepetitionTime"] for p in (EXTRAS / "bold_json").glob("*.json")]
    record("all bold.json TR == 1.4 (count of other values)", "all", sum(t != 1.4 for t in trs), 0, 0)
    record("number of bold.json files", "all", len(trs), 227, 0)

    # --- physio triggers, different edge rule
    with tarfile.open(ROOT / "data/LEMON/sub-032301.tar.gz") as tf:
        m = [x for x in tf.getmembers() if x.name.endswith("ses-01_task-rest_acq-AP_run-01_recording-ecg_physio.tsv.gz")][0]
        rows = gzip.decompress(tf.extractfile(m).read()).decode().split("\n")
    trig = [float(r.split()[1]) for r in rows if r.strip()]
    onsets = [k for k in range(len(trig)) if trig[k] > 0 and (k == 0 or trig[k - 1] == 0)]
    gaps = np.diff(onsets) / 1000.0
    record("physio trigger count (sub-032301)", "sub-010002", len(onsets), 657, 0)
    record("physio median trigger gap s", "sub-010002", float(np.median(gaps)), 1.4, 0.001)

    # --- header and voxel statistics
    for s in subs:
        path = ROOT / f"data/LEMON/MRI_MNI2mm/{s}_ses-01_task-rest_acq-AP_run-01_MNI2mm.nii.gz"
        hdr, d = read_nifti(path, want_data=True)
        record("header time points", s, hdr["dim"][3], 652, 0)
        record("header pixdim[4] (TR field)", s, hdr["pixdim"][3], cache[s]["zooms"][3], 1e-6)
        record("voxel size x (mm)", s, hdr["pixdim"][0], 2.0, 1e-6)
        record("sform x-offset (mm)", s, hdr["srow"][0][3], 90.0, 1e-4)
        brain = d["std"] > 0.4
        record("NaN count", s, d["nan"], cache[s]["n_nan"], 0)
        record("brain-like voxel count", s, int(brain.sum()), cache[s]["n_mask"], 0)
        record("voxels with any variation", s, int((d["std"] > 1e-6).sum()), cache[s]["n_mask_any"], 0)
        record("max |voxel mean| in brain", s, float(np.abs(d["mean"][brain]).max()), cache[s]["vox_mean_absmax"], 1e-6)
        share = float(((d["std"][brain] > 0.8) & (d["std"][brain] < 1.2)).mean())
        record("share of brain voxels with std 0.8-1.2", s, share, cache[s]["frac_vox_std_0p8_1p2"], 1e-4)

    # --- MeanFD from raw confounds text vs QC PDF
    for s in sorted(cache):
        a = p2a[s]
        if not (EXTRAS / "qc_pdf" / f"{a}_ses-01_task-rest_acq-AP_run-01_QC.pdf").exists():
            continue                                             # QC PDFs were downloaded for the 10 local scans only
        lines = (EXTRAS / "confounds" / f"{a}_ses-01_task-rest_acq-AP_run-01_confounds.txt").read_text().split("\n")
        rowsC = [[float(x) for x in ln.split()] for ln in lines if ln.strip()]
        fd = [sum(abs(rowsC[t][c] - rowsC[t - 1][c]) for c in (9, 10, 11)) for t in range(1, len(rowsC))]
        pdf = EXTRAS / "qc_pdf" / f"{a}_ses-01_task-rest_acq-AP_run-01_QC.pdf"
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        qc = float(txt.split("MeanFD = ")[1].split()[0])
        record("MeanFD: mean |diff| of columns 10-12 vs QC PDF", s, sum(fd) / len(fd), qc, 0.001)

    # --- same scan processed on two machines (laptop vs Colab): cached results must agree
    col = EDA / "cache_colab"
    # only scans processed on BOTH machines (raw scan on the laptop); the other Colab results were copied into the cache
    for s in sorted(set(local) & {p.stem for p in col.glob("sub-*.json")}):
        a, b = cache[s], json.loads((col / f"{s}.json").read_text())
        for k in ["n_mask", "n_mask_any", "n_nan", "value_min", "value_max", "gs_std", "neighbour_corr_mean",
                  "homotopic_corr_mean", "skew_median", "gs_lag1_autocorr"]:
            record(f"laptop vs Colab: {k}", s, b[k], a[k], 1e-6)
        za, zb = np.load(EDA / "cache" / f"{s}.npz"), np.load(col / f"{s}.npz")
        record("laptop vs Colab: arrays not bit-identical (count)", s,
               sum(not np.array_equal(za[k], zb[k], equal_nan=True) for k in zb.files), 0, 0)

    out = pd.DataFrame(res); out.to_csv(EDA / "verify_results.csv", index=False)
    # group-level summary without participant IDs (safe for Git)
    out["abs_diff"] = (out.independent.astype(float) - out.pipeline_value.astype(float)).abs()
    summ = out.assign(check=out.check.str.replace(r"\s*\(sub-\d{6}\)", "", regex=True)).groupby("check").agg(
        comparisons=("status", "size"), passed=("status", lambda x: int((x == "PASS").sum())),
        failed=("status", lambda x: int((x == "FAIL").sum())), max_abs_difference=("abs_diff", "max"), tolerance=("tolerance", "max")).reset_index()
    res_dir = ROOT / "analysis/fmri_eda/results"; res_dir.mkdir(exist_ok=True)
    summ.to_csv(res_dir / "verification_summary.csv", index=False)
    print(out.to_string(index=False)); print("\nPASS", (out.status == "PASS").sum(), "FAIL", (out.status == "FAIL").sum())


if __name__ == "__main__":
    main()
