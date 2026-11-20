#!/usr/bin/env python
"""fMRI EDA, step 2 of 3: checks register, tables and figures.

    uv run python analysis/fmri_eda/scripts/eda_report.py

Inputs (read-only): data/derived/fmri_eda/eda/cache (from eda_extract.py), data/LEMON/MRI_extras
(confounds, bold.json sidecars, QC PDFs), data/LEMON/sub-032301.tar.gz (physio with scanner triggers),
data/LEMON/name_match.csv, data/LEMON/Participants_LEMON.csv.
Needs the `pdftotext` command (poppler-utils) to read the QC PDFs.

Outputs (git-ignored, participant-level) in data/derived/fmri_eda/eda/:
  checks.csv          one row per verifiable claim: id, claim, method, value, expected, status
  per_scan_summary.csv, confounds_summary.csv, fc_summary.json
  figs/*.png          figures referenced by check id (see FINDINGS.md)

Group-level, de-identified copies (safe for Git) go to analysis/fmri_eda/:
  results/checks_group.csv, results/age_group_summary.csv
  figures/fig01-05, fig10-12 (people appear only as pseudonyms P001... + age group, or not at all; the
  P-to-ID key stays in data/derived/fmri_eda/eda/per_scan_summary.csv, column `pseudonym`)

Scaling (works for 10 or ~160 people): with more than 12 people, per-person panels become distributions and
time-course figures show only the people whose raw scan is on this laptop (SHOW); the age test switches from
exact to 10,000 random relabellings; F5 compares each person with 20 randomly chosen others; connectivity
matrices are float32 and the full-scan matrix is not kept. Confounds are read from the local text files when
the cache was made without them (Colab run).
"""
import io
import itertools
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
EDA = ROOT / "data/derived/fmri_eda/eda"
CACHE = EDA / "cache"
FIGS = EDA / "figs"
EXTRAS = ROOT / "data/LEMON/MRI_extras"
PHYSIO_TAR = ROOT / "data/LEMON/sub-032301.tar.gz"
TR = 1.4
N_DROPPED = 5
MNI2MM_AFFINE = np.array([[-2, 0, 0, 90], [0, 2, 0, -126], [0, 0, 2, -72], [0, 0, 0, 1]], float)

if FIGS.exists():
    shutil.rmtree(FIGS)          # only our own generated figures live here
FIGS.mkdir(parents=True)
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
                     "axes.titlesize": 10, "axes.titleweight": "bold"})

# ------------------------------------------------------------------ inputs
nm = pd.read_csv(ROOT / "data/LEMON/name_match.csv")
pa = pd.read_csv(ROOT / "data/LEMON/Participants_LEMON.csv", index_col=0).rename(
    columns={"Gender_ 1=female_2=male": "sex", "Age": "age_bin"})
p2a = dict(zip(nm.Initial_ID, nm.INDI_ID))
ids = sorted(p.stem for p in CACHE.glob("sub-*.json"))
J = {i: json.loads((CACHE / f"{i}.json").read_text()) for i in ids}
Z = {i: np.load(CACHE / f"{i}.npz") for i in ids}
for i in ids:                      # cache entries made on Colab without name_match.csv have archive_id None
    J[i]["archive_id"] = J[i].get("archive_id") or p2a[i]
A = {i: J[i]["archive_id"] for i in ids}
def _conf(i):                      # confounds: from the cache if stored there, else from the local text file (same file)
    if "confounds" in Z[i].files:
        return Z[i]["confounds"].astype(np.float64)
    return np.loadtxt(EXTRAS / "confounds" / f"{A[i]}_ses-01_task-rest_acq-AP_run-01_confounds.txt", ndmin=2)
CONF = {i: _conf(i) for i in ids}
NID = len(ids)
BIG = NID > 12                     # many people: per-person panels are replaced by distributions
ALPHA, LW = (0.25, 0.6) if BIG else (0.8, 0.9)
RAW = ROOT / "data/LEMON/MRI_MNI2mm"
# people shown individually in time-course figures: those whose raw scan is on this laptop (independently verified)
SHOW = [i for i in ids if (RAW / f"{i}_ses-01_task-rest_acq-AP_run-01_MNI2mm.nii.gz").exists()][:10] or ids[:10]
age = {i: pa.loc[A[i], "age_bin"] for i in ids}
older = {i: int(age[i].split("-")[0]) >= 55 for i in ids}
COL = {i: ("#c0392b" if older[i] else "#2471a3") for i in ids}       # red = older, blue = younger
PSEUDO = {i: (f"P{k + 1:03d}" if NID > 99 else f"P{k + 1:02d}") for k, i in enumerate(ids)}   # figure labels: pseudonym + age group, never the real ID
lab = {i: f"{PSEUDO[i]} ({'older' if older[i] else 'younger'})" for i in ids}
N = J[ids[0]]["shape"][3]

checks = []
def check(cid, section, claim, method, value, expected="", status="INFO", fig=""):
    checks.append(dict(id=cid, section=section, claim=claim, method=method, value=value, expected=expected,
                       status=status, figure=fig))
def ok(b):
    return "PASS" if bool(b) else "FAIL"
def rng_txt(v, nd=3):
    v = np.asarray(v, float); return f"{v.min():.{nd}f} to {v.max():.{nd}f}"

from math import comb as _ncomb
N_PERM = 10000
def perm_test(vals):
    """Two-sided permutation test of the older-vs-younger mean difference.
    Exact (all relabellings) when there are at most 20,000 of them; otherwise N_PERM random relabellings
    with a fixed seed, p = (count + 1) / (N_PERM + 1)."""
    v = np.array([vals[i] for i in ids], float); g = np.array([older[i] for i in ids])
    ok_ = ~np.isnan(v); v, g = v[ok_], g[ok_]
    obs = v[g].mean() - v[~g].mean(); n_old = int(g.sum())
    if _ncomb(len(v), n_old) <= 20000:
        cnt = tot = 0
        for cmb in itertools.combinations(range(len(v)), n_old):
            m = np.zeros(len(v), bool); m[list(cmb)] = True
            d = v[m].mean() - v[~m].mean(); tot += 1; cnt += abs(d) >= abs(obs) - 1e-12
        return obs, cnt / tot, tot, "exact"
    r = np.random.default_rng(0); cnt = 0
    for _ in range(N_PERM):
        m = r.permutation(g); cnt += abs(v[m].mean() - v[~m].mean()) >= abs(obs) - 1e-12
    return obs, (cnt + 1) / (N_PERM + 1), N_PERM, "random"

# ================================================================== A. timing (TR)
tr_hdr = sorted({J[i]["zooms"][3] for i in ids})
check("A1", "Timing", "Header TR (pixdim[4]) of the preprocessed files", "nibabel header zooms[3], all scans",
      f"{tr_hdr}", "documented 1.4 s", ok(tr_hdr == [1.4]))
bj = sorted((EXTRAS / "bold_json").glob("*_bold.json"))
trs = pd.Series([json.loads(p.read_text()).get("RepetitionTime") for p in bj])
check("A2", "Timing", "RepetitionTime in raw-scan bold.json sidecars", f"read {len(bj)} sidecars",
      f"{trs.value_counts().to_dict()}", "1.4 for all", ok(len(bj) > 0 and (trs == 1.4).all()), "fig01")
with tarfile.open(PHYSIO_TAR) as tf:
    mem = [m for m in tf.getmembers() if m.name.endswith("ses-01_task-rest_acq-AP_run-01_recording-ecg_physio.tsv.gz")][0]
    phys = pd.read_csv(io.BytesIO(tf.extractfile(mem).read()), sep="\t", header=None, compression="gzip").dropna(axis=1, how="all").values
    js = [m for m in tf.getmembers() if m.name.endswith("ses-01_task-rest_acq-AP_run-01_recording-ecg_physio.json")][0]
    pj = json.loads(tf.extractfile(js).read())
trig = phys[:, list(pj["Columns"]).index("trigger")]
on = np.flatnonzero((trig[1:] > 0.5) & (trig[:-1] <= 0.5)) + 1
if trig[0] > 0.5:
    on = np.r_[0, on]
iti = np.diff(on) / pj["SamplingFrequency"]
check("A3", "Timing", "Scanner trigger spacing in physio recording (1 participant, archive sub-032301)",
      f"rising edges of 'trigger' column at {pj['SamplingFrequency']} Hz",
      f"{len(on)} triggers; interval median {np.median(iti):.4f} s, min {iti.min():.4f}, max {iti.max():.4f}",
      "657 triggers 1.4 s apart", ok(len(on) == 657 and np.allclose(iti, 1.4, atol=0.002)), "fig01")
nt = sorted({J[i]["shape"][3] for i in ids})
check("A4", "Timing", "Time points per scan = acquired volumes - 5 dropped", "header dim[4]",
      f"{nt}; 657 - {N_DROPPED} = {657 - N_DROPPED}", "652", ok(nt == [652]))
check("A5", "Timing", "Usable scan duration", "652 x 1.4 s", f"{652 * TR:.1f} s = {652 * TR / 60:.2f} min", "", "INFO")
check("A6", "Timing", "Volumes after resampling to 2 s (as Brain-JEPA training data)", "652 x 1.4 / 2",
      f"{652 * TR / 2:.0f} volumes", "", "INFO")

fig, ax = plt.subplots(1, 3, figsize=(12, 3.3))
ax[0].hist(iti, bins=np.arange(1.38, 1.421, 0.002), color="#2471a3")
ax[0].set_title("A3: gap between scanner triggers"); ax[0].set_xlabel("seconds between triggers"); ax[0].set_ylabel("count")
ax[1].bar([str(k) for k in trs.value_counts().index], trs.value_counts().values, color="#2471a3")
ax[1].set_title("A2: TR in raw bold.json (all people)"); ax[1].set_xlabel("RepetitionTime (s)"); ax[1].set_ylabel("files")
ax[2].bar(["header (preprocessed)", "bold.json", "physio triggers"], [tr_hdr[0], trs.mode()[0], np.median(iti)],
          color=["#c0392b", "#2471a3", "#2471a3"])
ax[2].set_title("A1-A3: three sources of TR"); ax[2].set_ylabel("seconds")
for k, v in enumerate([tr_hdr[0], trs.mode()[0], np.median(iti)]):
    ax[2].text(k, v + 0.02, f"{v:.2f}", ha="center")
fig.tight_layout(); fig.savefig(FIGS / "fig01_timing_evidence.png"); plt.close(fig)

# ================================================================== B. geometry
same = {k: len({json.dumps(J[i][k]) for i in ids}) == 1 for k in ["shape", "zooms", "affine", "datatype", "descrip", "qform_code", "sform_code"]}
check("B1", "Geometry", "Header fields identical across scans", "compare shape/zooms/affine/datatype/descrip/q-sform",
      json.dumps(same), "all true", ok(all(same.values())))
aff = np.array(J[ids[0]]["affine"])
check("B2", "Geometry", "Grid is the standard FSL MNI152 2 mm grid", "affine vs [[-2,0,0,90],[0,2,0,-126],[0,0,2,-72]]",
      f"max abs diff {np.abs(aff - MNI2MM_AFFINE).max():.4f}; shape {J[ids[0]]['shape'][:3]}", "0 and 91x109x91",
      ok(np.allclose(aff, MNI2MM_AFFINE) and J[ids[0]]["shape"][:3] == [91, 109, 91]))
check("B3", "Geometry", "No slice-timing info and no scaling in header", "slice_duration, toffset, scl_slope",
      f"slice_duration {J[ids[0]]['slice_duration']}, toffset {J[ids[0]]['toffset']}, scl_slope {J[ids[0]]['scl_slope']}", "", "INFO")

# ================================================================== C. values
S = pd.DataFrame([dict(public_id=i, archive_id=A[i], age_bin=age[i], group="older" if older[i] else "younger",
                       sex={1: "F", 2: "M"}.get(pa.loc[A[i], "sex"], "?"), **{k: J[i][k] for k in J[i] if not isinstance(J[i][k], list) and k not in ("public_id", "archive_id")})
                  for i in ids])
check("C1", "Values", "No NaN or Inf values", "count over all voxels and volumes", f"NaN {S.n_nan.sum()}, Inf {S.n_inf.sum()}", "0",
      ok(S.n_nan.sum() == 0 and S.n_inf.sum() == 0))
check("C2", "Values", "Every voxel time series is mean-centred", "max |temporal mean| over brain voxels",
      f"{S.vox_mean_absmax.max():.2e}", "< 1e-5", ok(S.vox_mean_absmax.max() < 1e-5), "fig02")
med_std = [Z[i]["vstd_pct"][4] for i in ids]
check("C3", "Values", "Voxel temporal std is about 1 (variance-normalised)", "median of voxel std, brain-like voxels",
      f"medians {rng_txt(med_std)}; share of voxels with std 0.8-1.2: {rng_txt(S.frac_vox_std_0p8_1p2)}",
      "0.8-1.2", ok(min(med_std) > 0.8 and max(med_std) < 1.2), "fig02")
check("C4", "Values", "Signal distribution is near-Gaussian per voxel", "median skew / excess kurtosis of 30k voxels",
      f"skew {rng_txt(S.skew_median)}; kurtosis {rng_txt(S.kurt_excess_median)}", "|skew|<0.1, |kurt|<0.5",
      ok(S.skew_median.abs().max() < 0.1 and S.kurt_excess_median.abs().max() < 0.5), "fig02")
from scipy.ndimage import distance_transform_edt
from scipy.stats import binomtest
edge_std, core_std = [], []
for i in ids:
    dist_in = distance_transform_edt(Z[i]["mask"])
    st = Z[i]["std3"]
    edge_std.append(np.median(st[(dist_in > 0) & (dist_in <= 2)])); core_std.append(np.median(st[dist_in >= 6]))
edge_std, core_std = np.array(edge_std), np.array(core_std)
check("C6", "Values", "Std is lower at the brain edge than inside (z-scoring happened before the MNI warp, which averages voxels)",
      "median voxel std within 2 voxels of the mask edge vs >= 6 voxels inside", f"edge {rng_txt(edge_std)}; inside {rng_txt(core_std)}",
      "edge < inside in all", ok((edge_std < core_std).all()), "fig04")
check("C5", "Values", "Value range", "min / max over brain voxels", f"{S.value_min.min():.2f} to {S.value_max.max():.2f}", "", "INFO")

edges = Z[ids[0]]["hist_edges"]; ctr = (edges[:-1] + edges[1:]) / 2
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
for i in ids:
    h = Z[i]["hist_counts"]; d = np.where(h > 0, h / h.sum() / np.diff(edges), np.nan)
    ax[0].semilogy(ctr, d, color=COL[i], lw=LW, alpha=ALPHA)
ax[0].semilogy(ctr, np.exp(-ctr ** 2 / 2) / np.sqrt(2 * np.pi), "k--", lw=1, label="standard normal N(0,1)")
ax[0].set_ylim(1e-9, 2); ax[0].set_xlabel("signal value (standardised units)"); ax[0].set_ylabel("density (log scale)")
ax[0].set_title("C4: all brain values vs a bell curve"); ax[0].legend(frameon=False, fontsize=8)
for i in ids:
    ax[1].plot([0, 1, 5, 25, 50, 75, 95, 99, 100], Z[i]["vstd_pct"], "-o", color=COL[i], ms=3 if not BIG else 1.5, lw=LW, alpha=ALPHA)
ax[1].axhline(1, color="k", ls="--", lw=0.8); ax[1].set_xlabel("percentile of brain voxels"); ax[1].set_ylabel("temporal std")
ax[1].set_title("C3: how variable each voxel is (target 1)")
for a in ax:
    a.plot([], [], color="#c0392b", label="older"); a.plot([], [], color="#2471a3", label="younger"); a.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(FIGS / "fig02_value_distribution.png"); plt.close(fig)

# ================================================================== D. brain mask
near_empty = 1 - S.n_mask / S.n_mask_any
M = np.stack([Z[i]["mask"] for i in ids])
_Mf = M.reshape(NID, -1).astype(np.float32); _inter = _Mf @ _Mf.T; _sz = _Mf.sum(1)
dice = 2 * _inter / (_sz[:, None] + _sz[None, :]); del _Mf, _inter
offd = dice[~np.eye(len(ids), dtype=bool)]
gap = [int(Z[i]["std_hist_counts"][5:7].sum()) for i in ids]   # bins 0.2-0.3 and 0.3-0.4
check("D1", "Brain mask", "Voxels with any signal split into near-empty and brain-like groups",
      "voxel std histogram; brain-like = std > 0.4", f"near-empty share {rng_txt(near_empty)}; voxels in the 0.2-0.4 gap {min(gap)}-{max(gap)}",
      "", "INFO", "fig03")
check("D2", "Brain mask", "Brain-like voxels per scan", "count std > 0.4",
      f"{S.n_mask.min():,} to {S.n_mask.max():,} ({rng_txt(S.n_mask / S.n_voxels)} of grid)", "typical MNI brain 0.2-0.35 of grid",
      ok((S.n_mask / S.n_voxels).between(0.2, 0.35).all()), "fig04")
check("D3", "Brain mask", "Masks overlap across people", "pairwise Dice", f"min {offd.min():.3f}, mean {offd.mean():.3f}", "> 0.9",
      ok(offd.min() > 0.9), "fig04")

se = Z[ids[0]]["std_hist_edges"]
fig, ax = plt.subplots(figsize=(8, 3.5))
for i in ids:
    h = Z[i]["std_hist_counts"]; ax.step(range(len(h)), h, where="mid", color=COL[i], lw=LW, alpha=ALPHA)
ax.set_xticks(range(len(se) - 1)); ax.set_xticklabels([f"{a:.2g}" for a in se[:-1]], rotation=70, fontsize=7)
ax.axvline(6.5, color="k", ls="--", lw=0.8); ax.text(6.7, ax.get_ylim()[1] * 0.85, "brain-like: std > 0.4", fontsize=8)
ax.text(1, ax.get_ylim()[1] * 0.6, "outside brain\n(almost no signal)", fontsize=8)
ax.set_xlabel("voxel temporal std (lower edge of bin)"); ax.set_ylabel("number of voxels")
ax.set_title("D1: two kinds of voxels - empty padding and brain")
fig.tight_layout(); fig.savefig(FIGS / "fig03_voxel_std_histogram.png"); plt.close(fig)

def slices(ax_row, vol, cmap, vmin, vmax, label):
    c = [s // 2 for s in vol.shape]
    for a, sl, t in zip(ax_row, [vol[:, :, c[2]].T, vol[:, c[1], :].T, vol[c[0], :, :].T], ["axial (from above)", "coronal (from front)", "sagittal (from side)"]):
        im = a.imshow(sl, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax); a.set_title(t, fontsize=8, fontweight="normal"); a.axis("off")
    return im
fig, ax = plt.subplots(2, 3, figsize=(10, 6.4))
im = slices(ax[0], M.mean(0), "viridis", 0, 1, ""); fig.colorbar(im, ax=ax[0], shrink=0.8, label="share of people\nwith brain here")
ssum = np.zeros(M.shape[1:])
for i in ids:
    ssum += np.where(Z[i]["mask"], Z[i]["std3"], 0)
ms = np.where(M.any(0), ssum / np.maximum(M.sum(0), 1), np.nan)
im = slices(ax[1], ms, "magma", 0, 1.5, ""); fig.colorbar(im, ax=ax[1], shrink=0.8, label="mean voxel std")
fig.suptitle("D2-D3: where the brain is (top) and how variable it is (bottom)", fontweight="bold")
fig.savefig(FIGS / "fig04_brain_maps.png"); plt.close(fig)

# ================================================================== E. frequency content
f = Z[ids[0]]["freq_hz"]
spec = np.stack([Z[i]["spec_mean_voxel"] for i in ids]); spec[:, 0] = 0
specn = spec / spec.sum(1, keepdims=True)
below = specn[:, (f > 0) & (f < 0.01)].sum(1); inband = specn[:, (f >= 0.01) & (f <= 0.1)].sum(1); above = specn[:, f > 0.1].sum(1)
peak = f[specn.argmax(1)]
cum = np.cumsum(specn, 1); f99 = np.array([f[np.searchsorted(c, 0.99)] for c in cum])
check("E1", "Frequency", "Share of signal power below / inside / above 0.01-0.1 Hz (TR 1.4 s)", "FFT of 20k voxels per scan",
      f"below {rng_txt(below, 2)}; inside {rng_txt(inband, 2)}; above {rng_txt(above, 4)}",
      "not a sharp band: the pipeline uses a soft Gaussian filter (fslmaths -bptf), see E4", "INFO", "fig05")
check("E2", "Frequency", "Peak frequency and 99%-power frequency", "argmax / cumulative 99% of mean spectrum",
      f"peak {rng_txt(peak, 4)} Hz; 99% of power below {rng_txt(f99, 3)} Hz", "", "INFO", "fig05")
check("E3", "Frequency", "Power above 0.1 Hz is removed", "share of power above 0.1 Hz", f"max {above.max():.5f}", "< 0.01",
      ok(above.max() < 0.01), "fig05")
# pipeline filter (lsd_lemon: fslmaths -bptf, sigma_vol = 1/(2*TR*f_cut), TR hard-coded 1.4 s)
sig_lp = 1 / (2 * TR * 0.1) * TR; sig_hp = 1 / (2 * TR * 0.01) * TR          # seconds: 5 s and 50 s
H2 = np.exp(-4 * np.pi ** 2 * sig_lp ** 2 * f ** 2) * (1 - np.exp(-2 * np.pi ** 2 * sig_hp ** 2 * f ** 2)) ** 2
f_half = np.sqrt(np.log(2)) / (2 * np.pi * sig_lp)
win = (f >= 0.012) & (f <= 0.08)
mean_spec = specn.mean(0)
obs_range = np.log10(mean_spec[win].max() / mean_spec[win].min())
corr_range = np.log10((mean_spec[win] / H2[win]).max() / (mean_spec[win] / H2[win]).min())
check("E4", "Frequency", "Spectrum shape is explained by the pipeline's Gaussian band-pass (sigma 5 s low-pass, 50 s high-pass)",
      "spread (log10 range) of the mean spectrum over 0.012-0.08 Hz, before vs after dividing by the filter's power response",
      f"raw spread {obs_range:.2f} decades; after removing filter {corr_range:.2f} decades; low-pass half-power at {f_half:.4f} Hz",
      "after < half of raw", ok(corr_range < obs_range / 2), "fig05")
# data-driven version of E4: fit the low-pass width instead of taking it from the code
def spread_after(sl, sh=sig_hp):
    h = np.exp(-4 * np.pi ** 2 * sl ** 2 * f ** 2) * (1 - np.exp(-2 * np.pi ** 2 * sh ** 2 * f ** 2)) ** 2
    r = mean_spec[win] / h[win]
    # flatness of the residual: residual std of log10 after removing a straight line in log-log (allows a 1/f background)
    x = np.log10(f[win]); y = np.log10(r); c = np.polyfit(x, y, 1)
    return float(np.std(y - np.polyval(c, x)))
grid = np.arange(2.0, 10.01, 0.1)
fits = np.array([spread_after(g) for g in grid])
best = float(grid[fits.argmin()])
check("E5", "Frequency", "Low-pass width fitted from the data matches the pipeline setting: sigma = 1/(2*TR*0.1) volumes = 3.57 vol = 5 s with TR 1.4 (it would be 5 vol = 7 s if TR 1.0 had been used)",
      "grid search 2-10 s: Gaussian low-pass width that leaves the flattest residual (log-log line removed, 1/f allowed), 0.012-0.08 Hz",
      f"best fit {best:.1f} s; residual {fits.min():.3f} (best), {spread_after(5.0):.3f} at 5 s, {spread_after(7.0):.3f} at 7 s",
      "best fit within 4.5-5.5 s", ok(4.5 <= best <= 5.5), "fig05")
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
for i in ids:
    ax[0].semilogy(f[1:], specn[ids.index(i), 1:], color=COL[i], lw=LW, alpha=ALPHA)
    ax[1].plot(f, cum[ids.index(i)], color=COL[i], lw=LW, alpha=ALPHA)
for a in ax:
    a.axvspan(0.01, 0.1, color="#27ae60", alpha=0.12, label="documented band 0.01-0.1 Hz")
    a.set_xlabel("frequency (Hz, with the true TR 1.4 s)"); a.set_xlim(0, 0.36)
sc = mean_spec[win].mean() / H2[win].mean()
ax[0].semilogy(f[1:], (H2 * sc)[1:], "k--", lw=1.2, label="pipeline filter response (scaled)")
ax[0].set_ylim(1e-7, 1)
ax[0].set_ylabel("share of power (log)"); ax[0].set_title("E1/E4: how fast the signal fluctuates")
ax[1].set_ylabel("cumulative share of power"); ax[1].set_title("E2: power accumulated up to each frequency")
ax[0].legend(frameon=False, fontsize=7)
fig.tight_layout(); fig.savefig(FIGS / "fig05_power_spectrum.png"); plt.close(fig)

# ================================================================== F. confounds / motion
qc = {}
for i in ids:
    pdf = EXTRAS / "qc_pdf" / f"{A[i]}_ses-01_task-rest_acq-AP_run-01_QC.pdf"
    if pdf.exists():
        t = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
        m = re.search(r"MeanFD = ([0-9.]+)", t)
        ts = re.search(r"tSNR inside the mask\s*\n(?:.*\n)*?\s+([1-9][0-9]*\.[0-9]{3,})\s*\n", t)
        qc[i] = dict(qc_meanfd=float(m.group(1)) if m else np.nan, qc_median_tsnr=float(ts.group(1)) if ts else np.nan)
crow, fd_ts = [], {}
for i in ids:
    C = CONF[i]; n = C.shape[1]
    flags, trend = C[:, 18:n - 3], C[:, n - 3:]
    onehot = bool(flags.size == 0 or ((flags != 0).sum(0) == 1).all() and (flags.max(0) == 1).all())
    flagged = [int(np.flatnonzero(flags[:, c])[0]) for c in range(flags.shape[1])] if onehot else []
    diff_ok = min(abs(np.corrcoef(np.diff(C[:, 6 + q]), C[1:, 12 + q])[0, 1]) for q in range(6))
    trend_ok = bool(np.allclose(trend[:, 0], 1) and np.corrcoef(trend[:, 1], np.linspace(-1, 1, N))[0, 1] > 0.999)
    fd_tr = np.abs(C[1:, 15:18]).sum(1)                                  # pipeline-style FD: translations only
    fd_pw = fd_tr + 50 * np.abs(C[1:, 12:15]).sum(1)                     # Power et al. 2012 FD (rotations at 50 mm)
    fd_ts[i] = fd_pw
    tr_cols = C[:, 9:12]
    Pm = np.abs(np.fft.rfft(tr_cols - tr_cols.mean(0), axis=0)) ** 2
    crow.append(dict(public_id=i, n_cols=n, n_flagged=flags.shape[1], flags_one_hot=onehot, flagged_volumes=" ".join(map(str, flagged)),
                     c1_6_unit_norm=bool(np.allclose(np.linalg.norm(C[:, :6], axis=0), 1, atol=1e-2)),
                     c1_6_zero_mean=bool(np.abs(C[:, :6].mean(0)).max() < 1e-6), c13_18_diff_min_corr=diff_ok, trend_ok=trend_ok,
                     n_cols_eq_21_plus_flags=n == 21 + flags.shape[1],
                     fd_translation_mean=fd_tr.mean(), fd_power_mean=fd_pw.mean(), fd_power_max=fd_pw.max(),
                     n_fd_power_gt_0p5=int((fd_pw > 0.5).sum()),
                     translation_power_share_above_0p1hz=float(Pm[f > 0.1].sum() / Pm.sum()),
                     translation_abs_mean_mm=float(np.abs(tr_cols.mean(0)).max()),
                     r2_all=J[i].get("r2_all_median", np.nan), r2_random_same_n=J[i].get("r2_random_same_n_median", np.nan),
                     **qc.get(i, {})))
CS = pd.DataFrame(crow)
CS.to_csv(EDA / "confounds_summary.csv", index=False)
check("F1", "Confounds", "Column layout: 6 unit-norm + 6 params + 6 first differences + one-hot flags + 3 trends",
      "unit norm, zero mean, corr(diff(c7-12), c13-18), one-hot test, constant/linear test, ncol = 21 + flags",
      f"all {NID} files: unit-norm {CS.c1_6_unit_norm.all()}, diff corr min {CS.c13_18_diff_min_corr.min():.4f}, one-hot {CS.flags_one_hot.all()}, trends {CS.trend_ok.all()}, count rule {CS.n_cols_eq_21_plus_flags.all()}",
      "all true", ok(CS.c1_6_unit_norm.all() and CS.c1_6_zero_mean.all() and CS.c13_18_diff_min_corr.min() > 0.999 and CS.flags_one_hot.all() and CS.trend_ok.all() and CS.n_cols_eq_21_plus_flags.all()), "fig06")
hasqc = CS.qc_meanfd.notna()
dfd = (CS.fd_translation_mean - CS.qc_meanfd)[hasqc].abs()
check("F2", "Confounds", "Columns 10-12 are translations in mm: they reproduce the pipeline's MeanFD (QC PDF)",
      "mean over frames of sum |diff| of columns 10-12 vs MeanFD printed in QC PDF",
      f"{int(hasqc.sum())} people; max abs difference {dfd.max():.4f} mm; r = {np.corrcoef(CS.fd_translation_mean[hasqc], CS.qc_meanfd[hasqc])[0, 1]:.4f}",
      "difference < 0.001 mm", ok(hasqc.sum() > 0 and dfd.max() < 0.001), "fig07")
check("F3", "Confounds", "Pipeline MeanFD ignores rotations; Power FD (rotations at 50 mm) is higher",
      "Power FD mean vs pipeline MeanFD (translations only, recomputed = QC PDF value, see F2)",
      f"Power FD {rng_txt(CS.fd_power_mean)} vs pipeline-style {rng_txt(CS.fd_translation_mean)} mm (all {NID}); "
      f"Power FD higher in {int((CS.fd_power_mean > CS.fd_translation_mean).sum())}/{NID}", "", "INFO", "fig07")
check("F4", "Confounds", "Motion columns were not high-pass filtered (any high-pass removes the mean)",
      "max |mean| of translation columns 10-12 per person; share of translation power above 0.1 Hz (info)",
      f"max |mean| {rng_txt(CS.translation_abs_mean_mm, 3)} mm; power above 0.1 Hz {rng_txt(CS.translation_power_share_above_0p1hz, 2)}",
      "|mean| > 0.01 mm in all", ok(CS.translation_abs_mean_mm.min() > 0.01))
# F5: own confounds vs other people's confounds, on the 10 mm cube signals (computed further down, needs cubes)
_nf = CS.n_flagged.value_counts().sort_index()
check("F6", "Confounds", "Flagged (outlier) volumes per scan", "number of one-hot columns",
      (f"{CS.n_flagged.tolist()}" if not BIG else f"median {CS.n_flagged.median():.0f}, range {CS.n_flagged.min()}-{CS.n_flagged.max()}; "
       f"{int((CS.n_flagged == 0).sum())} scans with none; {int((CS.n_flagged > 20).sum())} with more than 20"), "", "INFO", "fig08")

fig, ax = plt.subplots(figsize=(10, 3.6))
C0 = CONF[ids[0]]
ax.imshow((C0 / (np.abs(C0).max(0) + 1e-12)).T, aspect="auto", cmap="RdBu_r", vmin=-1, vmax=1, interpolation="nearest")
for y, t in [(2.5, "1-6 noise components (aCompCor)"), (8.5, "7-12 motion: 7-9 rotation, 10-12 translation"), (14.5, "13-18 frame-to-frame change of 7-12"), (C0.shape[1] - 2, "last 3: constant, linear, quadratic trend")]:
    ax.text(N + 8, y, t, va="center", fontsize=8)
ax.set_xlim(0, N + 260); ax.set_xlabel("volume"); ax.set_ylabel("column")
ax.set_title(f"F1: layout of one confounds file ({PSEUDO[ids[0]]}; each column scaled to its maximum)")
fig.tight_layout(); fig.savefig(FIGS / "fig06_confounds_layout.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
m = hasqc
ax[0].scatter(CS.qc_meanfd[m], CS.fd_translation_mean[m], c=[COL[i] for i in CS.public_id[m]], s=40, label="translations only")
ax[0].scatter(CS.qc_meanfd[m], CS.fd_power_mean[m], c=[COL[i] for i in CS.public_id[m]], s=40, marker="x", label="Power FD (with rotations)")
lim = [0, max(CS.fd_power_mean.max(), CS.qc_meanfd.max()) * 1.1]
ax[0].plot(lim, lim, "k--", lw=0.8, label="perfect agreement"); ax[0].set_xlim(lim); ax[0].set_ylim(lim)
ax[0].set_xlabel("MeanFD printed in pipeline QC PDF (mm)"); ax[0].set_ylabel("our recomputation (mm)")
ax[0].set_title("F2-F3: our motion numbers vs the pipeline's"); ax[0].legend(frameon=False, fontsize=7)
if BIG:
    _b = np.linspace(0, CS.fd_translation_mean.max() * 1.05, 30)
    for g_, c_ in [(False, "#2471a3"), (True, "#c0392b")]:
        ax[1].hist(CS.fd_translation_mean[[older[i] == g_ for i in CS.public_id]], bins=_b, color=c_, alpha=0.6,
                   label="older" if g_ else "younger")
    ax[1].set_xlabel("MeanFD recomputed from confounds (mm)"); ax[1].set_ylabel("people"); ax[1].legend(frameon=False, fontsize=7)
    ax[1].set_title(f"Mean head motion, all {NID} people")
else:
    ax[1].bar(range(len(ids)), CS.qc_meanfd, color=[COL[i] for i in ids])
    ax[1].set_xticks(range(len(ids))); ax[1].set_xticklabels([lab[i] for i in ids], rotation=60, fontsize=7)
    ax[1].set_ylabel("MeanFD (mm)"); ax[1].set_title("Mean head motion per person (red = older)")
fig.tight_layout(); fig.savefig(FIGS / "fig07_meanfd_reproduction.png"); plt.close(fig)

fig, ax = plt.subplots(len(SHOW), 1, figsize=(11, 1.1 * len(SHOW)), sharex=True)
for r, i in enumerate(SHOW):
    ax[r].plot(np.arange(1, N), fd_ts[i], color=COL[i], lw=0.6)
    for v in [int(x) for x in CS.flagged_volumes[ids.index(i)].split()]:
        ax[r].axvline(v, color="k", lw=0.8, alpha=0.7)
    ax[r].set_ylabel(lab[i], rotation=0, labelpad=40, fontsize=7)
ax[0].set_title("F6: head movement between frames (Power FD, mm) with flagged outlier volumes (black lines)")
ax[-1].set_xlabel("volume"); fig.tight_layout(); fig.savefig(FIGS / "fig08_motion_timecourses.png"); plt.close(fig)

# ================================================================== G. time courses
first = S.dvars_first30_median / S.dvars_rest_median
check("G1", "Time courses", "Global signal is smooth", "lag-1 autocorrelation of global signal", rng_txt(S.gs_lag1_autocorr), "> 0.9",
      ok(S.gs_lag1_autocorr.min() > 0.9), "fig09")
check("G2", "Time courses", "Global signal explains little of each voxel", "median r^2 between voxel and global signal",
      rng_txt(S.gs_r2_median), "", "INFO")
check("G3", "Time courses", "First 30 volumes change more than the rest (edge effect)", "median DVARS first 30 / rest",
      f"ratio {rng_txt(first, 2)} (median {np.median(first):.2f}); higher in {int((first > 1.05).sum())} of {len(ids)} scans", "", "INFO", "fig09")
fig, ax = plt.subplots(len(SHOW), 2, figsize=(12, 1.15 * len(SHOW)), sharex=True)
for r, i in enumerate(SHOW):
    ax[r, 0].plot(np.arange(N) * TR / 60, Z[i]["gs"], color=COL[i], lw=0.7); ax[r, 0].set_ylabel(lab[i], rotation=0, labelpad=40, fontsize=7)
    ax[r, 1].plot(np.arange(1, N) * TR / 60, Z[i]["dvars"], color=COL[i], lw=0.7); ax[r, 1].axvspan(0, 30 * TR / 60, color="0.9")
ax[0, 0].set_title("G1: global signal (brain average)"); ax[0, 1].set_title("G3: DVARS (change between frames; grey = first 30)")
ax[-1, 0].set_xlabel("minutes"); ax[-1, 1].set_xlabel("minutes")
fig.tight_layout(); fig.savefig(FIGS / "fig09_global_signal_dvars.png"); plt.close(fig)
for i in SHOW:
    z = Z[i]
    fig, ax = plt.subplots(3, 1, figsize=(11, 5), gridspec_kw=dict(height_ratios=[1, 1, 4]), sharex=True)
    ax[0].plot(z["gs"], lw=0.7); ax[0].set_ylabel("global\nsignal")
    ax[1].plot(np.arange(1, N), fd_ts[i], lw=0.7, color="C3"); ax[1].set_ylabel("motion\nFD (mm)")
    ax[2].imshow(z["carpet"].astype(np.float32), aspect="auto", cmap="gray", vmin=-3, vmax=3, interpolation="nearest")
    ax[2].set_ylabel("2000 brain voxels"); ax[2].set_xlabel("volume")
    ax[0].set_title(f"{PSEUDO[i]} = {i} ({age[i]}): carpet plot - rows are voxels, columns are frames, grey = value (-3 to +3)")
    fig.tight_layout(); fig.savefig(FIGS / f"carpet_{i}.png"); plt.close(fig)

# ================================================================== H. spatial and functional structure
check("H1", "Spatial", "Neighbouring voxels are correlated (spatial smoothness)", "mean corr of voxel with +x neighbour (2 mm)",
      rng_txt(S.neighbour_corr_mean), "", "INFO", "fig10")
r_n = S.neighbour_corr_mean.values
fwhm = 2.355 * 2.0 / np.sqrt(-4 * np.log(r_n))
check("H2", "Spatial", "Implied smoothness (Gaussian approximation)", "FWHM = 2.355 * d / sqrt(-4 ln r), d = 2 mm",
      f"{rng_txt(fwhm, 2)} mm", "", "INFO")
hd = np.array([J[i]["homotopic_corr_mean"] - J[i]["homotopic_ctrl_corr_mean"] for i in ids])
check("H3", "Spatial", "Mirror (left-right) voxels correlate more than same-distance controls",
      "mean corr homotopic pairs minus y-shifted pairs at the same distance; sign test over people",
      f"difference {rng_txt(hd)}; positive in {int((hd > 0).sum())}/{len(ids)} (two-sided sign test p = {binomtest(int((hd > 0).sum()), len(ids)).pvalue:.2g})",
      "positive in all", ok((hd > 0).all()), "fig10")
# correlation vs distance
bins = np.arange(0, 162, 6)
cvd = np.array([[np.nanmean(np.where((Z[i]["pair_dist_mm"] >= lo) & (Z[i]["pair_dist_mm"] < lo + 6), Z[i]["pair_corr"], np.nan)) for lo in bins[:-1]] for i in ids])
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
for r, i in enumerate(ids):
    ax[0].plot(bins[:-1] + 3, cvd[r], color=COL[i], lw=LW, alpha=ALPHA)
ax[0].axhline(0, color="k", lw=0.6); ax[0].set_xlabel("distance between voxels (mm)"); ax[0].set_ylabel("mean correlation")
ax[0].set_title("H1: correlation falls with distance")
hx = np.array([J[i]["homotopic_ctrl_corr_mean"] for i in ids]); hy = np.array([J[i]["homotopic_corr_mean"] for i in ids])
ax[1].scatter(hx, hy, c=[COL[i] for i in ids], s=40 if not BIG else 12, alpha=0.8)
_l = [min(hx.min(), hy.min()) - 0.02, max(hx.max(), hy.max()) + 0.02]
ax[1].plot(_l, _l, "k--", lw=0.8, label="equal (no mirror effect)")
ax[1].set_xlabel("control pair, same distance: mean correlation"); ax[1].set_ylabel("left-right mirror pair: mean correlation")
ax[1].set_title("H3: mirror regions move together (one dot per person)"); ax[1].legend(frameon=False, fontsize=7)
fig.tight_layout(); fig.savefig(FIGS / "fig10_spatial_structure.png"); plt.close(fig)

# ---- connectivity on 10 mm cubes present in everyone (>= 60 of 125 voxels)
common = None
for i in ids:
    good = set(Z[i]["cube_id"][Z[i]["cube_nvox"] >= 60].tolist())
    common = good if common is None else common & good
common = np.array(sorted(common))
CT = {i: Z[i]["cube_ts"][np.searchsorted(Z[i]["cube_id"], common)].astype(np.float32) for i in ids}   # load once
def cube_ts(i, sl=slice(None)):
    return CT[i][:, sl].astype(np.float64)
iu = np.triu_indices(len(common), 1)
def r2_cubes(Y, Cm):
    Cm = np.c_[Cm, np.ones(len(Cm))]
    beta, *_ = np.linalg.lstsq(Cm, Y, rcond=None); res = Y - Cm @ beta
    return float(np.median(1 - (res ** 2).sum(0) / ((Y - Y.mean(0)) ** 2).sum(0)))
base = {i: np.c_[CONF[i][:, :18], CONF[i][:, -3:]] for i in ids}   # 6 aCompCor + 12 motion + 3 trends
N_OTHER = min(20, NID - 1)        # compare with a fixed random sample of other people (all others when few)
_ro = np.random.default_rng(1)
own_r2, other_r2 = [], []
for i in ids:
    Y = cube_ts(i).T
    oth = [o for o in ids if o != i]
    oth = oth if len(oth) <= N_OTHER else list(_ro.choice(oth, N_OTHER, replace=False))
    own_r2.append(r2_cubes(Y, base[i])); other_r2.append(np.median([r2_cubes(Y, base[o]) for o in oth]))
own_r2, other_r2 = np.array(own_r2), np.array(other_r2)
CS["r2_own_confounds_cubes"] = own_r2; CS["r2_other_confounds_cubes_median"] = other_r2
CS.to_csv(EDA / "confounds_summary.csv", index=False)
check("F5", "Confounds", "Consistent with confounds already regressed out: own confounds explain less of the signal than other people's (main evidence is the pipeline code order)",
      f"median R2 over 10 mm cubes, own 21 base columns vs the median over {N_OTHER} other people's columns" + (" (random sample)" if N_OTHER < NID - 1 else ""),
      f"own {rng_txt(own_r2)}; others {rng_txt(other_r2)}; own lower in {int((own_r2 < other_r2).sum())}/{len(ids)}",
      "own < others in all", ok((own_r2 < other_r2).all()))
def fc(ts):
    return np.arctanh(np.clip(np.corrcoef(ts)[iu], -0.999999, 0.999999)).astype(np.float32)
half = N // 2
cc = np.array([[int(c // 10000), int(c // 100 % 100), int(c % 100)] for c in common]) * 10.0
dd = np.sqrt(((cc[iu[0]] - cc[iu[1]]) ** 2).sum(1))
db = np.arange(0, 160, 10)
dbin = [(dd >= lo) & (dd < lo + 10) for lo in db[:-1]]
npair = len(iu[0])
F1 = np.empty((NID, npair), np.float32); F2 = np.empty((NID, npair), np.float32)
mean_fc = np.empty(NID); Fsum = np.zeros(npair); prof = np.full((NID, len(dbin)), np.nan)
for r, i in enumerate(ids):            # full-scan matrix is used once and not kept (memory)
    F1[r] = fc(cube_ts(i, slice(0, half))); F2[r] = fc(cube_ts(i, slice(half, N)))
    ff = fc(cube_ts(i)); mean_fc[r] = ff.mean(dtype=np.float64); Fsum += ff
    prof[r] = [np.tanh(ff[b].mean(dtype=np.float64)) if b.any() else np.nan for b in dbin]
def _zrows(F):                         # standardise rows in place: then corr = dot product / n
    F -= F.mean(1, keepdims=True, dtype=np.float64).astype(np.float32); F /= F.std(1, keepdims=True, dtype=np.float64).astype(np.float32)
    return F
sim = (_zrows(F1).astype(np.float64) @ _zrows(F2).astype(np.float64).T) / npair
within = np.diag(sim); between = sim[~np.eye(len(ids), dtype=bool)]
ident = float(np.mean([np.argmax(sim[a]) == a for a in range(len(ids))]))
check("H4", "Connectivity", "Connectivity pattern is reproducible within a scan (first half vs second half)",
      f"{len(common)} cubes (10 mm) present in all scans; corr of Fisher-z connectivity, half 1 vs half 2",
      f"within-person {rng_txt(within)} (median {np.median(within):.3f}); between-person {rng_txt(between)} (median {np.median(between):.3f}); "
      f"own > every other person in {int((within[:, None] > np.where(np.eye(NID, dtype=bool), -np.inf, sim)).all(1).sum())}/{NID}",
      "within > between", ok(within.min() > between.max()), "fig11")
check("H5", "Connectivity", "A person can be identified from their own connectivity ('fingerprinting')",
      "for each person, is the most similar second-half matrix their own?", f"{ident * 100:.0f}% correct (chance {100 / len(ids):.0f}%)", "> chance",
      ok(ident > 1 / len(ids)), "fig11")
check("H6", "Connectivity", "Average connectivity strength (mean Fisher-z over all cube pairs)", "mean of upper triangle",
      rng_txt(mean_fc), "", "INFO", "fig11")
order = np.lexsort((cc[:, 2], cc[:, 1], cc[:, 0]))
Mfc = np.eye(len(common)); Mfc[iu] = np.tanh(Fsum / NID); Mfc = Mfc + Mfc.T - np.eye(len(common))
fig, ax = plt.subplots(1, 3, figsize=(13, 4))
im = ax[0].imshow(Mfc[np.ix_(order, order)], cmap="RdBu_r", vmin=-0.8, vmax=0.8)
fig.colorbar(im, ax=ax[0], shrink=0.8, label="correlation"); ax[0].set_title(f"H6: group connectivity, {len(common)} cubes")
ax[0].set_xlabel("cube (ordered left-right, then back-front)"); ax[0].set_ylabel("cube")
im = ax[1].imshow(sim, cmap="viridis"); fig.colorbar(im, ax=ax[1], shrink=0.8, label="similarity of connectivity")
if not BIG:
    ax[1].set_xticks(range(len(ids))); ax[1].set_yticks(range(len(ids)))
    ax[1].set_xticklabels([PSEUDO[i] for i in ids], rotation=60, fontsize=7); ax[1].set_yticklabels([PSEUDO[i] for i in ids], fontsize=7)
else:
    ax[1].set_xticks([]); ax[1].set_yticks([])
ax[1].set_xlabel("people, second half of scan"); ax[1].set_ylabel("people, first half of scan"); ax[1].set_title("H4-H5: own (diagonal) vs others' matrices")
for r, i in enumerate(ids):
    ax[2].plot(db[:-1] + 5, prof[r], color=COL[i], lw=LW, alpha=ALPHA)
ax[2].axhline(0, color="k", lw=0.6); ax[2].set_xlabel("distance between cube centres (mm)"); ax[2].set_ylabel("mean correlation")
ax[2].set_title("Connectivity vs distance")
fig.tight_layout(); fig.savefig(FIGS / "fig11_connectivity.png"); plt.close(fig)
json.dump(dict(n_cubes=int(len(common)), within=within.tolist(), between_mean=float(between.mean()), identification=ident,
               mean_fc=mean_fc.tolist()), open(EDA / "fc_summary.json", "w"), indent=1)

# ================================================================== I. older vs younger (descriptive)
S = S.merge(CS[["public_id", "qc_meanfd", "qc_median_tsnr", "fd_power_mean", "n_flagged"]], on="public_id")
S["pseudonym"] = [PSEUDO[i] for i in S.public_id]; S["mean_fc"] = mean_fc; S["split_half_reliability"] = within
S.to_csv(EDA / "per_scan_summary.csv", index=False)
rows = []
S = S.merge(CS[["public_id", "fd_translation_mean"]], on="public_id")
# MeanFD recomputed from the confounds (identical to the QC-PDF value, F2) is available for everyone; tSNR only from QC PDFs
AGE_MEASURES = [("fd_translation_mean", "MeanFD (mm)"), ("mean_fc", "mean connectivity"), ("split_half_reliability", "split-half FC reliability"),
                ("gs_std", "global signal std"), ("n_flagged", "flagged volumes")]
if S.qc_median_tsnr.notna().all():
    AGE_MEASURES.insert(1, ("qc_median_tsnr", "median tSNR (QC PDF)"))
n_old, n_young = int(sum(older.values())), NID - int(sum(older.values()))
for col, nice in AGE_MEASURES:
    d, p, tot, kind = perm_test(dict(zip(S.public_id, S[col])))
    o = S[S.group == "older"][col]; y = S[S.group == "younger"][col]
    sd = np.sqrt(((len(o) - 1) * o.var() + (len(y) - 1) * y.var()) / (len(o) + len(y) - 2))
    rows.append(dict(measure=nice, n_older=len(o), n_younger=len(y), older_mean=o.mean(), younger_mean=y.mean(), difference=d,
                     cohens_d=d / sd if sd > 0 else np.nan, perm_p=p, n_perm=tot, perm_kind=kind))
G = pd.DataFrame(rows)
for _, r in G.iterrows():
    check(f"I{_ + 1}", "Age groups", f"{r.measure}: older vs younger (descriptive)", f"{r.perm_kind} permutation test, {r.n_perm} relabellings, n = {r.n_older} older vs {r.n_younger} younger",
          f"older {r.older_mean:.3f}, younger {r.younger_mean:.3f}, Cohen's d {r.cohens_d:.2f}, p = {r.perm_p:.4f}", "", "INFO", "fig12")
fig, ax = plt.subplots(1, len(G), figsize=(13, 3.2))
for a, (col, nice) in zip(ax, AGE_MEASURES):
    for gi, g in enumerate(["younger", "older"]):
        v = S[S.group == g][col]
        a.scatter(np.full(len(v), gi) + np.random.default_rng(gi).uniform(-0.15, 0.15, len(v)), v, color=["#2471a3", "#c0392b"][gi],
                  s=30 if not BIG else 8, alpha=0.9 if not BIG else 0.5)
        a.plot([gi - 0.2, gi + 0.2], [v.mean()] * 2, "k-")
    p = G[G.measure == nice].perm_p.iloc[0]
    a.set_xticks([0, 1]); a.set_xticklabels(["younger", "older"]); a.set_title(f"{nice}\np = {p:.3g}", fontsize=9)
fig.suptitle(f"I: older vs younger ({n_old} vs {n_young}, descriptive; bar = group mean)", fontweight="bold")
fig.tight_layout(); fig.savefig(FIGS / "fig12_age_groups.png"); plt.close(fig)

# ================================================================== write
CK = pd.DataFrame(checks)
CK.to_csv(EDA / "checks.csv", index=False)
G.to_csv(EDA / "age_group_summary.csv", index=False)
print(CK[["id", "status", "value"]].to_string(max_colwidth=110))
print("\nPASS", (CK.status == "PASS").sum(), "FAIL", (CK.status == "FAIL").sum(), "INFO", (CK.status == "INFO").sum())

# ================================================================== publish group-level outputs to analysis/fmri_eda
TASK = ROOT / "analysis/fmri_eda"
RES, PUBFIG = TASK / "results", TASK / "figures"
RES.mkdir(exist_ok=True); PUBFIG.mkdir(exist_ok=True)
CKg = CK.copy()
for col in ["claim", "method", "value"]:
    CKg[col] = (CKg[col].astype(str).str.replace(r",?\s*archive sub-\d{6}", "", regex=True)
                .str.replace(r"sub-\d{6}", "[id removed]", regex=True))
assert not CKg.astype(str).apply(lambda c: c.str.contains(r"sub-\d{6}")).any().any()
CKg.to_csv(RES / "checks_group.csv", index=False)
G.drop(columns=[]).to_csv(RES / "age_group_summary.csv", index=False)
PUBLISH = ["fig01_timing_evidence.png", "fig02_value_distribution.png", "fig03_voxel_std_histogram.png", "fig04_brain_maps.png",
           "fig05_power_spectrum.png", "fig10_spatial_structure.png", "fig11_connectivity.png", "fig12_age_groups.png"]
for old in PUBFIG.glob("fig*.png"):
    old.unlink()
for fn in PUBLISH:
    shutil.copy2(FIGS / fn, PUBFIG / fn)
print(f"published {len(PUBLISH)} figures to {PUBFIG.relative_to(ROOT)} and 2 tables to {RES.relative_to(ROOT)}")
