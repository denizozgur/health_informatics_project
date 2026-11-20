#!/usr/bin/env python
"""Task 3 EDA, step 1 of 3: read each complete MNI2mm scan ONCE and cache compact summaries.

    uv run python analysis/fmri_eda/scripts/eda_extract.py              # all complete local scans (skips cached)
    uv run python analysis/fmri_eda/scripts/eda_extract.py --force      # recompute everything
    uv run python analysis/fmri_eda/scripts/eda_extract.py sub-010002   # only these public IDs
    uv run python analysis/fmri_eda/scripts/eda_extract.py --workers 4  # several scans at once

Other locations (e.g. Google Colab with the scans in one flat Google Drive folder):
    python eda_extract.py --mri-dir /content/drive/MyDrive/ecqPSQdata --conf-dir /content/drive/MyDrive/ecqPSQdata \
        --name-match /content/drive/MyDrive/ecqPSQdata/name_match.csv --cache-dir /content/drive/MyDrive/task3_cache --workers 6

Read-only on the scans. Writes data/derived/fmri_eda/eda/cache/<public_id>.npz + .json (git-ignored).
Step 2 (eda_report.py) builds checks, tables and figures from the cache.
Step 3 (eda_verify.py) recomputes key numbers from the raw files with independent code.

Reproducibility: every random sample uses a generator seeded from the participant number,
so results do not depend on processing order.
"""
import argparse
import gzip
import io
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

try:                       # Intel ISA-L gzip: same output, about 2-3x faster decompression; optional
    from isal import igzip as _gz
except ImportError:
    _gz = gzip

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[3] if len(_HERE.parents) > 3 else Path.cwd()   # repo root; cwd when run standalone (Colab)
MRI = ROOT / "data/LEMON/MRI_MNI2mm"
CONF = ROOT / "data/LEMON/MRI_extras/confounds"
CACHE = ROOT / "data/derived/fmri_eda/eda/cache"

TR_TRUE = 1.4          # verified in eda_report.py (bold.json sidecars + physio triggers), NOT the header value
BRAIN_STD_MIN = 0.4    # "brain-like" voxel = temporal std > 0.4 (sits in the gap of the bimodal std histogram)
STD_EDGES = np.concatenate([[0, 1e-6, 0.01, 0.05, 0.1, 0.2, 0.3, 0.4], np.arange(0.5, 1.51, 0.1), [3, 100]])
N_SPEC_VOX = 20000     # voxels sampled for spectra / confound R2
N_CARPET = 2000        # voxels shown in the carpet plot
N_PAIRS = 300000       # random voxel pairs for correlation-vs-distance
N_HOMO = 40000         # voxels sampled for the left-right (homotopic) test
CUBE = 5               # grid parcellation: 5x5x5 voxels = 10 mm cubes
MIRROR_I = 90          # x = -2*i + 90  ->  x = 0 at i = 45, mirror index i' = 90 - i


def read_scan(p):
    """Decompress the whole .nii.gz once into memory. Raises EOFError/OSError if the file is truncated,
    so a complete read doubles as the completeness check (the old gzip_ok pass read every file twice)."""
    with _gz.open(p, "rb") as f:
        raw = f.read()
    return nib.Nifti1Image.from_stream(io.BytesIO(raw))


def rowcorr(A, B):
    """Pearson correlation of matching rows of A and B."""
    A = A - A.mean(1, keepdims=True); B = B - B.mean(1, keepdims=True)
    return (A * B).sum(1) / np.sqrt((A * A).sum(1) * (B * B).sum(1) + 1e-12)


def process(pub, indi, path, conf_dir=CONF, cache=CACHE):
    rng = np.random.default_rng(int(pub.split("-")[1]))
    img = read_scan(path)
    h = img.header
    D = np.asarray(img.dataobj, dtype=np.float32)  # x, y, z, t
    nx, ny, nz, T = D.shape
    out, info = {}, {}

    # ---- 1. header
    info.update(
        public_id=pub, archive_id=indi, shape=list(D.shape), zooms=[float(z) for z in h.get_zooms()],
        datatype=str(h.get_data_dtype()), xyzt_units=list(h.get_xyzt_units()),
        qform_code=int(h["qform_code"]), sform_code=int(h["sform_code"]), affine=np.round(img.affine, 4).tolist(),
        slice_duration=float(h["slice_duration"]), toffset=float(h["toffset"]),
        descrip=bytes(h["descrip"]).decode("ascii", "ignore").strip("\x00"),
        scl_slope=float(h["scl_slope"]) if np.isfinite(h["scl_slope"]) else None,
        file_bytes=Path(path).stat().st_size,
        n_nan=int(np.isnan(D).sum()), n_inf=int(np.isinf(D).sum()),
    )

    # ---- 2. masks
    std3 = D.std(axis=-1)
    mask_any = std3 > 1e-6
    mask = std3 > BRAIN_STD_MIN
    info.update(n_voxels=int(mask.size), n_mask_any=int(mask_any.sum()), n_mask=int(mask.sum()),
                n_exact_zero=int((~mask_any).sum()))
    out["std_hist_edges"] = STD_EDGES
    out["std_hist_counts"] = np.histogram(std3[mask_any], bins=STD_EDGES)[0]
    out["std3"] = std3.astype(np.float32); out["mask"] = mask
    out["vol0"] = D[..., 0].copy(); out["vol_mid"] = D[..., T // 2].copy()

    # ---- 3. value distribution and voxel statistics (brain-like voxels)
    X = D[mask]                                  # (nv, T)
    nv = X.shape[0]
    edges = np.linspace(-10, 10, 201)
    hist = np.zeros(200, np.int64)
    for i in range(0, nv, 50000):
        hist += np.histogram(X[i:i + 50000], bins=edges)[0]
    out["hist_edges"] = edges; out["hist_counts"] = hist
    vmean = X.mean(1, dtype=np.float64); vstd = X.std(1, dtype=np.float64)
    out["vstd_pct"] = np.percentile(vstd, [0, 1, 5, 25, 50, 75, 95, 99, 100])
    info.update(value_min=float(X.min()), value_max=float(X.max()), vox_mean_absmax=float(np.abs(vmean).max()),
                frac_vox_std_0p8_1p2=float(((vstd > 0.8) & (vstd < 1.2)).mean()))
    s = rng.choice(nv, size=min(30000, nv), replace=False)
    z = (X[s] - X[s].mean(1, keepdims=True)) / np.maximum(X[s].std(1, keepdims=True), 1e-9)
    info["skew_median"] = float(np.median((z ** 3).mean(1)))
    info["kurt_excess_median"] = float(np.median((z ** 4).mean(1) - 3))

    # ---- 4. whole-brain time courses
    gs = X.mean(0, dtype=np.float64)
    dv = np.sqrt((np.diff(X, axis=1) ** 2).mean(0, dtype=np.float64))   # DVARS, length T-1
    out["gs"] = gs; out["dvars"] = dv; out["spatial_std"] = X.std(0)
    info.update(gs_std=float(gs.std()), gs_lag1_autocorr=float(np.corrcoef(gs[:-1], gs[1:])[0, 1]),
                dvars_first30_median=float(np.median(dv[:30])), dvars_rest_median=float(np.median(dv[30:])))

    # ---- 5. spectra (mean over sampled voxels) and variance explained by global signal
    sp = rng.choice(nv, size=min(N_SPEC_VOX, nv), replace=False)
    Xs = X[sp].astype(np.float64)
    out["spec_mean_voxel"] = (np.abs(np.fft.rfft(Xs, axis=1)) ** 2).mean(0)
    out["spec_gs"] = np.abs(np.fft.rfft(gs - gs.mean())) ** 2
    out["freq_hz"] = np.fft.rfftfreq(T, d=TR_TRUE)
    cg = rowcorr(Xs, np.broadcast_to(gs, Xs.shape))
    out["corr_with_gs"] = cg.astype(np.float32)
    info["gs_r2_median"] = float(np.median(cg ** 2))

    # ---- 6. spatial structure: neighbours, distance, left-right mirror
    both = mask[:-1] & mask[1:]
    ii = np.argwhere(both); ii = ii[rng.choice(len(ii), size=min(40000, len(ii)), replace=False)]
    r = rowcorr(D[ii[:, 0], ii[:, 1], ii[:, 2]], D[ii[:, 0] + 1, ii[:, 1], ii[:, 2]])
    info["neighbour_corr_mean"] = float(r.mean())
    coords = np.argwhere(mask)                              # same order as X
    Xz = (X - X.mean(1, keepdims=True)) / np.maximum(X.std(1, keepdims=True), 1e-9)
    a = rng.integers(0, nv, N_PAIRS); b = rng.integers(0, nv, N_PAIRS)
    keep = a != b; a, b = a[keep], b[keep]
    dist = 2.0 * np.sqrt(((coords[a] - coords[b]) ** 2).sum(1))
    rr = np.empty(len(a), np.float32)
    for i in range(0, len(a), 20000):
        rr[i:i + 20000] = (Xz[a[i:i + 20000]] * Xz[b[i:i + 20000]]).mean(1)
    out["pair_dist_mm"] = dist.astype(np.float32); out["pair_corr"] = rr
    # homotopic: voxel (i,j,k) vs mirror (90-i,j,k); control: same-distance shift along y
    lin = -np.ones(mask.shape, np.int64); lin[mask] = np.arange(nv)
    cand = coords[(coords[:, 0] != 45)]
    mi = MIRROR_I - cand[:, 0]
    ok = (mi >= 0) & (mi < nx)
    cand, mi = cand[ok], mi[ok]
    ok = mask[mi, cand[:, 1], cand[:, 2]]
    cand, mi = cand[ok], mi[ok]
    d_vox = np.abs(cand[:, 0] - mi)
    yc = cand[:, 1] + d_vox * np.where(rng.random(len(cand)) < 0.5, 1, -1)
    ok = (yc >= 0) & (yc < ny)
    cand, mi, d_vox, yc = cand[ok], mi[ok], d_vox[ok], yc[ok]
    ok = mask[cand[:, 0], yc, cand[:, 2]]
    cand, mi, d_vox, yc = cand[ok], mi[ok], d_vox[ok], yc[ok]
    pick = rng.choice(len(cand), size=min(N_HOMO, len(cand)), replace=False)
    cand, mi, d_vox, yc = cand[pick], mi[pick], d_vox[pick], yc[pick]
    i0 = lin[cand[:, 0], cand[:, 1], cand[:, 2]]
    hm = (Xz[i0] * Xz[lin[mi, cand[:, 1], cand[:, 2]]]).mean(1)
    ct = (Xz[i0] * Xz[lin[cand[:, 0], yc, cand[:, 2]]]).mean(1)
    out["homo_corr"] = hm.astype(np.float32); out["homo_ctrl_corr"] = ct.astype(np.float32)
    out["homo_dist_mm"] = (2.0 * d_vox).astype(np.float32)
    info["homotopic_corr_mean"] = float(hm.mean()); info["homotopic_ctrl_corr_mean"] = float(ct.mean())

    # ---- 7. carpet sample
    out["carpet"] = X[rng.choice(nv, size=min(N_CARPET, nv), replace=False)].astype(np.float16)

    # ---- 8. grid parcellation (10 mm cubes; atlas-free, same grid for everyone because all scans share MNI space)
    cid = (coords[:, 0] // CUBE) * 10000 + (coords[:, 1] // CUBE) * 100 + (coords[:, 2] // CUBE)
    ucid, inv, cnt = np.unique(cid, return_inverse=True, return_counts=True)
    P = np.zeros((len(ucid), T), np.float64)
    np.add.at(P, inv, X)
    P /= cnt[:, None]
    out["cube_id"] = ucid; out["cube_nvox"] = cnt; out["cube_ts"] = P.astype(np.float32)

    # ---- 9. confounds: variance of the data explained by them (if already regressed out, R2 ~ chance p/T)
    cf = Path(conf_dir) / f"{indi}_ses-01_task-rest_acq-AP_run-01_confounds.txt"
    if indi and cf.exists():
        C = np.loadtxt(cf, ndmin=2)
        out["confounds"] = C.astype(np.float32)
        Y = Xs.T
        def r2(Cm):
            beta, *_ = np.linalg.lstsq(Cm, Y, rcond=None)
            res = Y - Cm @ beta
            return float(np.median(1 - (res ** 2).sum(0) / ((Y - Y.mean(0)) ** 2).sum(0)))
        n = C.shape[1]
        info.update(r2_all_median=r2(C), r2_compcor6_median=r2(np.c_[C[:, :6], np.ones(T)]),
                    r2_motion12_median=r2(np.c_[C[:, 6:18], np.ones(T)]), n_confounds=n)
        # same test on 21 random regressors gives the chance level empirically
        R = rng.standard_normal((T, n))
        info["r2_random_same_n_median"] = r2(R)

    # write to temporary names, then rename: the .json appears last and marks the participant as done,
    # so an interrupted run (e.g. a Colab disconnect) never leaves a half-written cache entry
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    with open(cache / f".{pub}.npz.part", "wb") as f:
        np.savez_compressed(f, **out)
    os.replace(cache / f".{pub}.npz.part", cache / f"{pub}.npz")
    (cache / f".{pub}.json.part").write_text(json.dumps(info, indent=1))
    os.replace(cache / f".{pub}.json.part", cache / f"{pub}.json")
    return info


def _run_one(pub, indi, path, conf_dir, cache):
    """Worker wrapper: returns a status line instead of raising, so one bad file never stops the batch."""
    t0 = time.time()
    try:
        process(pub, indi, path, conf_dir, cache)
        return pub, "ok", f"{time.time() - t0:.0f}s"
    except (EOFError, OSError, gzip.BadGzipFile) as e:
        return pub, "SKIP incomplete", repr(e)[:120]
    except Exception as e:  # noqa: BLE001 - reported and counted, never silently dropped
        return pub, "ERROR", repr(e)[:300]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="only these public IDs (sub-0100xx); always recomputed")
    ap.add_argument("--force", action="store_true", help="recompute even if cached")
    ap.add_argument("--mri-dir", default=MRI, type=Path, help="folder with *_MNI2mm.nii.gz (searched recursively)")
    ap.add_argument("--conf-dir", default=CONF, type=Path, help="folder with *_confounds.txt")
    ap.add_argument("--name-match", default=ROOT / "data/LEMON/name_match.csv", type=Path)
    ap.add_argument("--cache-dir", default=CACHE, type=Path)
    ap.add_argument("--workers", default=1, type=int, help="scans processed at once (~8 GB RAM each)")
    a = ap.parse_args()

    p2a = {}
    if a.name_match.exists():
        nm = pd.read_csv(a.name_match)
        p2a = dict(zip(nm.Initial_ID, nm.INDI_ID))
    else:
        print(f"WARNING: {a.name_match} not found -> no archive IDs, confound checks skipped", flush=True)

    todo, seen = [], set()
    for p in sorted(Path(a.mri_dir).rglob("sub-*_MNI2mm.nii.gz")):
        pub = p.name.split("_")[0]
        if pub in seen or (a.ids and pub not in a.ids):
            continue
        seen.add(pub)
        if (a.cache_dir / f"{pub}.json").exists() and not (a.force or a.ids):
            print("cached", pub, flush=True); continue
        todo.append((pub, p2a.get(pub), p, a.conf_dir, a.cache_dir))
    print(f"{len(seen)} scans found, {len(todo)} to process, {a.workers} worker(s)", flush=True)

    counts, t0 = {}, time.time()
    if a.workers <= 1:
        results = (_run_one(*t) for t in todo)
    else:
        ex = ProcessPoolExecutor(max_workers=a.workers)
        results = (f.result() for f in as_completed([ex.submit(_run_one, *t) for t in todo]))
    for k, (pub, status, note) in enumerate(results, 1):
        counts[status] = counts.get(status, 0) + 1
        print(f"[{k}/{len(todo)}] {status} {pub} {note}  (elapsed {(time.time() - t0) / 60:.1f} min)", flush=True)
    print("done", counts, flush=True)


if __name__ == "__main__":
    main()
