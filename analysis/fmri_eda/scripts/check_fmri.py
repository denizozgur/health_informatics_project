#!/usr/bin/env python
"""Task 3: read-only inventory and sanity check of the preprocessed LEMON fMRI (MNI2mm).

Run from the project root:
    uv run python analysis/fmri_eda/scripts/check_fmri.py

Reads (never modifies):
  data/LEMON/MRI_MNI2mm/          downloaded scans (complete files and in-progress .tmp_* folders)
  data/LEMON/name_match.csv       public ID (sub-0100xx) -> archive ID (sub-0323xx)
  data/LEMON/Participants_LEMON.csv  age bin and sex, keyed by archive ID
  data/derived/fmri_eda/s3_listing_lemon.tsv  size<TAB>key listing of the public S3 archive

Writes (all under data/derived/fmri_eda/, which is git-ignored):
  participant_table.csv, local_scan_checks.csv, remote_inventory_summary.json
Plus a group-level copy without IDs (safe for Git): analysis/fmri_eda/results/archive_summary.json

Nothing is guessed: anything not measured is written as "not checked" or UNCLEAR.
A scan is only called complete when gzip can read it to the end. For incomplete
files the header is still read, and signal statistics use only the leading
volumes that could be decoded; these rows are labelled PARTIAL.
"""
import gzip
import json
import re
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
MRI_DIR = ROOT / "data/LEMON/MRI_MNI2mm"
OUT = ROOT / "data/derived/fmri_eda"
LISTING = OUT / "s3_listing_lemon.tsv"
PREFIX = "data/Projects/INDI/MPI-LEMON/"
MAX_VOLS_FOR_STATS = 150  # incomplete files only: stats use the leading volumes that could be decoded


# ---------------------------------------------------------------- remote inventory
def remote_inventory():
    k = pd.read_csv(LISTING, sep="\t", header=None, names=["size", "key"])
    k["key"] = k.key.str.replace(PREFIX, "", regex=False)
    pre = k[k.key.str.contains("MRI_MPILMBB_LEMON/MRI_Preprocessed_Derivetives/", regex=False)].copy()
    pre["indi"] = pre.key.str.extract(r"(sub-\d+)")[0]
    flat = pre[~pre.key.str.endswith(".tar.gz")]
    rows = {}
    for kind, pat in [("mni", "_MNI2mm.nii.gz"), ("native", "_native.nii.gz"),
                      ("confounds", "_confounds.txt"), ("qc_pdf", "_QC.pdf"),
                      ("anat", "_brain.nii.gz")]:
        s = flat[flat.key.str.endswith(pat)].set_index("indi")["size"]
        rows[kind] = s
    tars = pre[pre.key.str.endswith(".tar.gz")].set_index("indi")["size"]
    rows["tar"] = tars
    return pd.DataFrame(rows), flat


# ---------------------------------------------------------------- local scans
def find_local_scans():
    """Yield (id_in_filename, path) for every MNI2mm file under the download folder."""
    for p in sorted(MRI_DIR.rglob("*_MNI2mm.nii.gz")):
        m = re.match(r"(sub-\d+)_", p.name)
        indi_in_name = m.group(1)
        yield indi_in_name, p


def gzip_complete(path):
    try:
        with gzip.open(path, "rb") as f:
            while f.read(1 << 24):
                pass
        return True
    except (EOFError, OSError, zlib.error):
        return False


def read_partial(path, max_vols, stats_wanted=True):
    """Read the NIfTI-1 header and as many leading volumes as can be decoded (max_vols)."""
    with gzip.open(path, "rb") as f:
        hdr = f.read(348)
        sizeof, = struct.unpack("<i", hdr[:4])
        if sizeof != 348:
            raise ValueError("not little-endian NIfTI-1")
        dim = struct.unpack("<8h", hdr[40:56])
        datatype, bitpix = struct.unpack("<2h", hdr[70:74])
        pixdim = struct.unpack("<8f", hdr[76:108])
        vox_offset, scl_slope, scl_inter = struct.unpack("<3f", hdr[108:120])
        xyzt_units = hdr[123]
        magic = hdr[344:348]
        f.read(int(vox_offset) - 348)
        nx, ny, nz, nt = dim[1:5]
        if datatype != 16:
            raise ValueError(f"unexpected datatype {datatype}")
        vol_bytes = nx * ny * nz * 4

        def gen():
            for _ in range(nt if max_vols is None else min(nt, max_vols)):
                try:
                    buf = f.read(vol_bytes)
                except (EOFError, OSError, zlib.error):
                    return
                if len(buf) < vol_bytes:
                    return
                yield np.frombuffer(buf, dtype="<f4").reshape(nx, ny, nz, order="F")

        meta = dict(shape=(nx, ny, nz, nt), voxel_mm=pixdim[1:4], tr_header_s=pixdim[4],
                xyzt_units=xyzt_units, scl_slope=scl_slope, scl_inter=scl_inter, magic=magic.decode("ascii", "ignore"))
        stats = signal_stats(gen(), ) if stats_wanted else {}
    return meta, stats


def signal_stats(vols):
    """Streaming per-voxel mean/std over all decoded volumes (float64 accumulators, low memory)."""
    n = 0
    n_nan = n_inf = 0
    sm = sq = None
    vmin, vmax = np.inf, -np.inf
    for v in vols:
        v = v.astype(np.float64)
        n_nan += int(np.isnan(v).sum()); n_inf += int(np.isinf(v).sum())
        v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
        if sm is None:
            sm = np.zeros_like(v); sq = np.zeros_like(v)
        sm += v; sq += v * v; n += 1
        vmin = min(vmin, float(v.min())); vmax = max(vmax, float(v.max()))
    if n < 10:
        return {}
    mean_t = sm / n
    std_t = np.sqrt(np.maximum(sq / n - mean_t ** 2, 0))
    nonconst = std_t > 1e-6
    return dict(
        n_vols_read=n, n_nan=n_nan, n_inf=n_inf,
        vox_total=int(nonconst.size), vox_nonconstant=int(nonconst.sum()), vox_frac_nonconstant=float(nonconst.mean()),
        value_min=vmin, value_max=vmax,
        voxmean_median=float(np.median(mean_t[nonconst])), voxmean_absmax=float(np.abs(mean_t[nonconst]).max()),
        voxstd_median=float(np.median(std_t[nonconst])),
        voxstd_p1=float(np.percentile(std_t[nonconst], 1)), voxstd_p99=float(np.percentile(std_t[nonconst], 99)),
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    nm = pd.read_csv(ROOT / "data/LEMON/name_match.csv")
    pt = pd.read_csv(ROOT / "data/LEMON/Participants_LEMON.csv", index_col=0)
    pt.index.name = "indi"
    pt = pt.rename(columns={"Gender_ 1=female_2=male": "sex", "Age": "age_bin"})
    master = pd.read_csv(ROOT / "data/derived/participant_table/master_table.csv", usecols=["participant_id", "age_bin_text"])

    inv, flat = remote_inventory()

    # ---- local scans
    local_rows = []
    pub2arch = dict(zip(nm.Initial_ID, nm.INDI_ID))
    for name_id, path in find_local_scans():
        # finished files are renamed to the PUBLIC id (sub-0100xx); in-progress files keep the archive id (sub-0323xx)
        is_public = name_id in pub2arch
        indi = pub2arch.get(name_id, name_id)
        row = dict(file=str(path.relative_to(ROOT)), archive_id=indi, file_bytes=path.stat().st_size,
                   name_carries="public_id" if is_public else "archive_id")
        row["gzip_complete"] = gzip_complete(path)
        try:
            meta, stats = read_partial(path, None if row["gzip_complete"] else MAX_VOLS_FOR_STATS)
            row.update(shape=str(meta["shape"]), n_timepoints_header=meta["shape"][3],
                       voxel_mm=str(tuple(round(float(v), 3) for v in meta["voxel_mm"])),
                       tr_header_s=round(float(meta["tr_header_s"]), 4), xyzt_units=meta["xyzt_units"],
                       scl_slope=meta["scl_slope"], scl_inter=meta["scl_inter"], magic=meta["magic"])
            row.update(stats)
        except Exception as e:  # report, do not hide
            row["header_error"] = repr(e)
        local_rows.append(row)
    local = pd.DataFrame(local_rows)
    local.to_csv(OUT / "local_scan_checks.csv", index=False)

    # ---- participant table (all 227/228 public IDs)
    t = nm.rename(columns={"Initial_ID": "participant_id", "INDI_ID": "archive_id"}).copy()
    t = t.merge(master, on="participant_id", how="left")
    t = t.merge(pt[["sex", "age_bin"]], left_on="archive_id", right_index=True, how="left")
    t = t.merge(inv, left_on="archive_id", right_index=True, how="left")
    t["remote_mni2mm"] = t["mni"].notna()
    t["remote_motion_file"] = t["confounds"].notna()
    t["remote_qc_pdf"] = t["qc_pdf"].notna()
    if len(local):
        # best (complete preferred) local row per archive id; the in-progress archive id is the one in the file name
        best = local.sort_values("gzip_complete", ascending=False).drop_duplicates("archive_id")
        bl = best.set_index("archive_id")
        t["local_scan"] = t.archive_id.map(lambda a: "none" if a not in bl.index else
                                           ("complete" if bl.loc[a, "gzip_complete"] else "INCOMPLETE (download running or truncated)"))
        t["n_timepoints_header"] = t.archive_id.map(bl["n_timepoints_header"]) if "n_timepoints_header" in bl else np.nan
    else:
        t["local_scan"] = "none"
        t["n_timepoints_header"] = np.nan
    t["n_timepoints_header"] = t["n_timepoints_header"].astype("Int64").astype(object).where(t.n_timepoints_header.notna(), "not checked")
    # confounds files downloaded to data/LEMON/MRI_extras/confounds (headerless text; column meaning UNCLEAR)
    cdir = ROOT / "data/LEMON/MRI_extras/confounds"
    def conf_info(a):
        f = cdir / f"{a}_ses-01_task-rest_acq-AP_run-01_confounds.txt"
        if not f.exists():
            return (np.nan, np.nan, np.nan)
        x = np.loadtxt(f, ndmin=2)
        return (x.shape[0], x.shape[1], bool(np.isfinite(x).all()))
    ci = t.archive_id.map(conf_info)
    t["confounds_rows"] = ci.map(lambda v: v[0])
    t["confounds_cols"] = ci.map(lambda v: v[1])
    t["confounds_all_finite"] = ci.map(lambda v: v[2])
    t["motion_data_available"] = np.where(t.confounds_rows.notna(), "yes: confounds file (column meaning decoded, see eda_findings.md F1-F2)", np.where(t.remote_motion_file, "listed in archive; not downloaded", "no"))

    size_gb = t["mni"] / 1e9
    med = size_gb.median()
    issues = []
    for i, r in t.iterrows():
        s = []
        if pd.isna(r.archive_id):
            s.append("no archive ID in name_match.csv")
        if not r.remote_mni2mm:
            s.append("no MNI2mm file in archive" + ("" if pd.notna(r.tar) else " (no preprocessed tar at all)"))
        elif size_gb[i] < 0.9 * med:
            s.append(f"MNI2mm file small ({size_gb[i]:.2f} GB vs median {med:.2f}); possibly shorter scan - UNCLEAR")
        if r.remote_mni2mm and not r.remote_qc_pdf:
            s.append("no QC pdf")
        if r.remote_mni2mm and not r.remote_motion_file:
            s.append("no confounds file")
        if pd.isna(r.age_bin_text):
            s.append("not in the 227-person META list (no age/sex in master table)")
        elif pd.notna(r.age_bin) and r.age_bin_text != r.age_bin:
            s.append("age bin differs between tables")
        issues.append("; ".join(s))
    t["issues"] = issues
    t["has_scan_in_archive"] = np.where(t.remote_mni2mm, "yes", "no")
    cols = ["participant_id", "archive_id", "age_bin", "sex", "has_scan_in_archive", "local_scan", "n_timepoints_header",
            "motion_data_available", "confounds_rows", "confounds_cols", "remote_qc_pdf", "issues"]
    t["mni_gb"] = (t["mni"] / 1e9).round(3)
    t[cols + ["mni_gb"]].to_csv(OUT / "participant_table.csv", index=False)

    summ = dict(
        participants_in_name_match=int(len(nm)),
        preprocessed_tars=int(inv["tar"].notna().sum()),
        mni2mm_files=int(inv["mni"].notna().sum()),
        confounds_files=int(inv["confounds"].notna().sum()),
        qc_pdfs=int(inv["qc_pdf"].notna().sum()),
        mni2mm_total_GB=float(inv["mni"].sum() / 1e9),
        tar_total_GB=float(inv["tar"].sum() / 1e9),
        mni2mm_gb_min_median_max=[float(inv["mni"].min() / 1e9), float(inv["mni"].median() / 1e9), float(inv["mni"].max() / 1e9)],
        no_mni2mm=t.loc[~t.remote_mni2mm, "participant_id"].tolist(),
        local_files=int(len(local)),
        local_complete=int(local["gzip_complete"].sum()) if len(local) else 0,
    )
    (OUT / "remote_inventory_summary.json").write_text(json.dumps(summ, indent=2))
    # group-level copy without participant IDs (safe for Git)
    pub = {k: v for k, v in summ.items() if k != "no_mni2mm"}
    pub["n_without_mni2mm"] = len(summ["no_mni2mm"])
    pub["n_in_227_meta_list_with_mni2mm"] = int((t.remote_mni2mm & t.age_bin_text.notna()).sum())
    res_dir = ROOT / "analysis/fmri_eda/results"; res_dir.mkdir(exist_ok=True)
    (res_dir / "archive_summary.json").write_text(json.dumps(pub, indent=2))
    print(json.dumps(summ, indent=2))
    if len(local):
        keep = [c for c in ["archive_id", "gzip_complete", "shape", "voxel_mm", "tr_header_s", "n_vols_read", "n_nan",
                            "vox_frac_nonconstant", "value_min", "value_max", "voxmean_median", "voxmean_absmax",
                            "voxstd_median", "voxstd_p1", "voxstd_p99"] if c in local.columns]
        print(local[keep].to_string())


if __name__ == "__main__":
    sys.exit(main())
