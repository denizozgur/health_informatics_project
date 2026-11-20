# fMRI EDA findings: preprocessed LEMON resting-state fMRI (159 scans)

**What this is.** The same checks as the earlier 10-scan pilot, run on every scan processed so far:

- **159 people:** 113 younger (20-40) and 46 older (55-80); 115 male and 44 female.
- **Where they come from:** 150 were processed on Google Colab from the shared Drive folder and 10 on the laptop. One person was in both runs.
- **What is not covered:** 63 of the 221 scans in the public archive are not here. They were not in the Drive folder, apart from one scan whose file is corrupt (see "Missing" below).

Every check has an ID in square brackets. The ID matches a row in [`results/checks_group.csv`](results/checks_group.csv) and a label in the figures in [`figures/`](figures/). Figures label people only by pseudonym (P001-P159) and age group, or not at all.

**How to re-run:**
- On Colab: [`colab/fmri_extract_colab.ipynb`](colab/fmri_extract_colab.ipynb).
- On the laptop:
  - `uv run python analysis/fmri_eda/scripts/eda_report.py` (about 4 min);
  - `uv run python analysis/fmri_eda/scripts/eda_verify.py --all` (about 10 min).

## Result at a glance

Checks: **19 PASS, 5 FAIL, 19 INFO.** The independent verification passes **115 of 115** comparisons.

| | Question | Answer for 159 scans | Check |
|---|---|---|---|
| 1 | Same format everywhere? | Yes: 652 time points, the same MNI 2 mm grid and identical header fields in every file | A4, B1, B2 |
| 2 | Real TR? | 1.4 s. The header still says 1.0 s in every file (known header error, the expected FAIL) | A1-A3 |
| 3 | Values sensible? | Yes: no NaN or Inf, every voxel mean-centred, std about 0.87-0.90, near-Gaussian | C1-C6 |
| 4 | Brain mask consistent? | Yes, apart from **one outlier scan (P077)** with an extra rim of "brain" | D1-D3 (D2, D3 FAIL) |
| 5 | Frequency content? | As in the pilot: the pipeline's Gaussian filter explains the spectrum shape; the fitted low-pass width is 4.7 s vs 5 s in the code | E1-E5 |
| 6 | Confounds file understood? | Yes: the column layout holds in all 159 files | F1 |
| 7 | Confounds already removed from the signal? | Yes for 156/159; 3 exceptions | F5 (FAIL) |
| 8 | Behaves like real brain signal? | Yes: mirror coupling in 159/159 people | H3 |
| 9 | Connectivity person-specific? | Yes: every person is identified correctly (100%; chance 0.6%). The strict "no overlap at all" rule fails | H4 (FAIL), H5 |
| 10 | Older vs younger? | Older people move twice as much. No clear difference in connectivity | I1-I5 |

## What changed from the pilot (10 scans)

- **The pilot's conclusions held.**
  - TR: 1.4 s.
  - Value range: z-scored, std about 0.9.
  - Filter: the Gaussian band-pass explains the spectrum.
  - Confounds: the layout is understood.
  - Signal: mirror coupling and person-specific connectivity.
- **Four checks that passed on 10 now fail on 159.** All four are explained below; none points to a problem with the data as a whole.
- **Two new things appeared:**
  - one scan with an unusual brain mask (P077);
  - a large age difference in head motion.

## The FAIL results, explained

**A1: header TR.** This is expected and the same as in the pilot. Every file says 1.0 s, but the true value is 1.4 s, confirmed by the 227 bold.json sidecars, the physio triggers and the filter fit.

**D2 and D3: one scan with an unusual brain mask (P077).**
- **D2 (brain share of the grid):** P077 has 35.2% of the grid as brain-like, just above the 35% limit. Everyone else is between 26.5% and 34%.
- **D3 (mask overlap between people):** the lowest pairwise overlap (Dice) is 0.83, below the 0.9 limit. All 158 pairs under 0.9 involve P077. Without P077, the lowest overlap is 0.903, so every pair passes.
- **What it looks like:** P077 has about 41,000 "brain" voxels where fewer than 10% of other people have any. They form a rim at the top, front and back of the brain. The QC image is `data/derived/fmri_eda/eda/figs/qc_P077_mask.png`; it is not in Git because it shows one person.
- **Cause: UNCLEAR.** It could be a large head, a slightly off registration to MNI space, or non-brain tissue left in the mask. Head motion is low for this person (MeanFD 0.09 mm).
- **Suggestion:** keep P077, but flag it, and repeat the key results without it as a sensitivity check.

**F5: own confounds should explain less signal than other people's.**
- This holds for 156 of 159 people, which supports "confounds were already regressed out", as the pipeline code says.
- The 3 exceptions (P035, P050, P135) have own R² 0.07-0.11 against others' 0.06-0.07. Two have higher-than-usual motion or many flagged frames (MeanFD 0.45 mm; 15 flagged frames).
- The check failed only because its rule was "in all people". Each person is now compared with 20 randomly chosen others instead of everyone, which is a method change from the pilot.

**H4: own connectivity vs other people's.**
- **The rule:** a person's lowest first-half-vs-second-half similarity must beat the highest similarity between any two different people.
- **The values:** with 159 people, the lowest own value (0.37) is below the highest cross-person value (0.44), so it fails.
- **Why it doesn't matter:** each person's own similarity is higher than their similarity to every one of the other 158 people, for all 159. The median own similarity is 0.51 vs 0.22 between people. Fingerprinting (H5) is correct for 100%.
- **Conclusion:** the rule was too strict for a large sample; the property it tests holds. The rule was not changed, so this stays recorded as a FAIL.

## Other results worth knowing

- **Head motion [F3, F6, I1].**
  - MeanFD (translations only, as in the pipeline QC) has a median of 0.14 mm. 8 people are above 0.3 mm and 1 is above 0.5 mm.
  - Power FD, which also counts rotations, is higher in every person.
  - Flagged outlier frames per scan: median 4, range 0-29. 15 scans have none.
- **Age and motion [I1, fig12].**
  - Older people move about twice as much: MeanFD 0.23 vs 0.12 mm.
  - Cohen's d is 1.8, which is a very large effect. Permutation p = 0.0001 (10,000 random relabellings).
  - **This matters for any age analysis:** motion has to be controlled, or age effects will be partly motion effects.
- **Age and connectivity [I2-I5].**
  - Mean connectivity is 0.167 vs 0.154 (p = 0.24).
  - Split-half reliability is 0.53 vs 0.51 (p = 0.14).
  - Global signal and flagged frames show no clear difference.
  - Mean connectivity correlates with motion (r = 0.25), so even these small differences may partly reflect motion.
  - All of these are descriptive. Five tests were run, with no correction for multiple comparisons.
- **Connectivity grid.** 1,730 cubes of 10 mm are present in all 159 scans, against 2,024 in the 10-scan pilot. Cubes at the brain edge drop out as more people are added.
- **Edge effect [G3].** The first 30 frames change more than the rest in 19 of 159 scans; the median ratio is 0.97. The pilot suggested a general start-of-scan effect, but in the full sample it affects only a minority.

## Missing

- **One corrupt scan (not processed, so no pseudonym; its ID is in `data/derived/fmri_eda/missing_scans.txt`, not in Git):** the file is damaged inside. Colab failed with "invalid deflate symbol". The archive copy is also unusually small: 1.96 GB, while the median is 2.26 GB. It is most likely corrupt at the source, but this is not yet confirmed by reading it with standard gzip.
- **63 archive scans** were not in the Drive folder, so they are not processed. Their IDs are listed in `data/derived/fmri_eda/missing_scans.txt` (not in Git). The extraction can be resumed for them on Colab or locally; finished people are skipped.
- **P143:** processed on Colab from the Drive copy, although the S3 listing of the public archive has no MNI2mm file for it. Where the Drive copy came from is UNCLEAR.

## Verification (115 of 115 PASS)

The full table is [`results/verification_summary.csv`](results/verification_summary.csv).

- **Independent re-reading of the 10 raw scans on the laptop.** Separate code checks:
  - header fields, NaN count and voxel counts;
  - voxel mean and std;
  - MeanFD against the QC PDFs.

  All match the cache exactly, or within the tolerance stated in the table.
- **Same scan, two machines.** P004 was processed on both the laptop and Colab:
  - every saved array is bit-identical;
  - summary numbers agree to 3e-9 (float rounding on a different CPU).
- **What is not independently re-checked:** the other 149 Colab scans. Their raw files are not on the laptop. They were produced by the same code, which the two-machine test above shows gives the same results.

## Limits

- **Coverage:** 159 of 221 archive scans. The missing ones are not random: they are mostly consecutive ID ranges, so age and sex mix may differ from the full cohort.
- **Parcellation:** the 10 mm cubes are a placeholder. Real features need an atlas, which is not on disk.
- **Voxel-level confound R²:** the pilot's voxel-level confound checks need the raw scans, so they exist only for the 10 local people. F5 (cube level) covers everyone.
- **Methods that changed with the sample size (disclosed):**
  - the age test uses random instead of exact permutations;
  - F5 compares each person with 20 others instead of all;
  - the age measures use MeanFD recomputed from the confounds instead of the QC-PDF value, because QC PDFs exist only for 10 people (F2 shows the two are identical);
  - tSNR was dropped from the age comparison for the same reason.
