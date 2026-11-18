# Task 3 - Preprocessed fMRI check (LEMON, MNI 2 mm)

Status date: 2026-11-19. **Only 3 complete scans were on disk when this was written (a 10-scan download by another session was still running).** Items marked *archive listing* come from the public S3 file list for all participants; items marked *measured* come from files opened locally. Anything neither is UNCLEAR. Originals were not modified. Script: `analysis/task3/check_fmri.py`. Participant-level table: `data/derived/task3/participant_table.csv` (git-ignored).

## 1. What is there
- Local folder `data/LEMON/MRI_MNI2mm/`: 3 finished scans, named `sub-0100xx_ses-01_task-rest_acq-AP_run-01_MNI2mm.nii.gz` (public ID), about 2.2-2.3 GB each; plus in-progress `.tmp_*` folders (archive ID sub-0323xx inside) from the running download.
- Archive (*listing*): one `.tar.gz` per person (222 tars, 578 GB total, about 2.6 GB each). Per person: `func/..._MNI2mm.nii.gz` (221 people, 496 GB, 1.96-2.30 GB each), `..._native.nii.gz`, `..._confounds.txt` (222), `..._QC.pdf` (219), and `anat/..._brain.nii.gz` (221). Only run-01 AP of session 1 (LEMON protocol); no masks or logs listed.
- IDs: public `sub-0100xx` (behavioural tables) vs archive `sub-0323xx` (MRI). Mapping is `data/LEMON/name_match.csv` (228 rows). `Participants_LEMON.csv` uses archive IDs.

## 2. Participants (*listing*)
- 221 of 228 mapped IDs have an MNI2mm scan. 228 = the 227 in the META list plus sub-010313, who has a scan but no age/sex. So **220 of the 227** have a scan.
- 7 have none (6 have no preprocessed tar at all, 1 has a tar without MNI2mm). IDs are in the table. No duplicates; naming is uniform.
- sub-010227 has a notably smaller file (1.96 GB vs median 2.26 GB); cause UNCLEAR (shorter scan or other).
- Age bins of all 228 mapped IDs: 20-30 y: 140; 30-40 y: 14; 55-80 y: 74 (no one 40-55; consistent with the young/old design). Not broken down by scan availability.

## 3. Scan contents (*measured*: 3 complete scans with all 652 volumes, plus 7 partial scans using their first volumes only; only the first ~10 archive IDs, so age coverage is narrow)
- Grid 91 x 109 x 91, voxel 2.0 mm, float32, no scaling. **652 time points** (= 657 - 5, matches the pipeline description), identical in every opened file.
- **Header TR = 1.0 s, not the documented 1.4 s.** The header value is probably a placeholder; true TR is UNCLEAR and must be checked before any timing-dependent step (Brain-JEPA expects about 2 s).
- Values: no NaN/Inf. Voxel temporal means are 0 (about 1e-16): mean-centering confirmed. **Temporal std is not 1**: median across voxels 0.64-0.71 in full scans, 1st-99th percentile of voxel std about 0 to 1.1. So "variance-normalised" is only approximately true (probably normalised before band-pass). About 58% of the grid has a nonzero signal; the rest is exactly 0 (outside a mask). Signals range about -9 to +9.

## 4. Motion and quality
- Per person `*_confounds.txt` (downloaded, 222 files, 51 MB, in `data/LEMON/MRI_extras/`): headerless, **652 rows each (matches the scan)**, all finite, but **21 to 147 columns depending on the person**. Column meaning is UNCLEAR. Likely a fixed block (21 columns: possibly motion parameters, compCor and trend terms) plus extra per-person columns (possibly one per flagged outlier volume); this is a hypothesis, not verified.
- No ready motion summary (no framewise displacement or mean-motion file) in the listing. A usable covariate needs the column definitions first.
- QC PDFs exist for 219 people (not downloaded, 5 MB each).

## 5. Failures
- No failure log in the archive. Implicit failures: 7 people with no MNI2mm; 2 people with an MNI2mm scan but no QC PDF (sub-010267, sub-010268).

## 6. Storage
- One scan: 91x109x91x652 x 4 B = 2.35 GB uncompressed (about 2.2 GB gzip); tar 2.6 GB. All 221 = 496 GB (MNI2mm only) or 578 GB (tars). Free disk: about 154 GB. **It will not fit.** Plan: stream each tar, parcellate, keep only regional time series, delete the scan. Download speed observed is about 100 KB/s per connection (about 7 h per tar); budget accordingly.

## Unanswered questions
1. True TR (header 1.0 s vs documented 1.4 s) and which is right for 652 volumes.
2. Meaning and order of the confounds columns; what makes the count vary (21-147).
3. Why the signal is not unit variance, and why 42% of the grid is exactly zero (mask definition, which atlas space).
4. Whether any archive-side motion summary exists (needs QC PDFs or the original rapidart outputs).
5. Why sub-010227's file is smaller; why sub-010302 has a tar but no MNI2mm.
6. Scans with fewer or more than 652 volumes: only checked for opened files; the rest need a header read after download.
7. Age coverage of the checked sample (not yet young/old balanced).
