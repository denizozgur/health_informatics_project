# ECG during the fMRI scan

This step screens the ECG recorded during the resting-state fMRI. It checks whether each recording is complete and readable, whether its timing matches the scan, and whether automatic heartbeat detection looks plausible. **No heart-rate-variability (HRV) values are computed yet**, and no participant has been declared usable: that needs manual beat review first.

**See the results:** [overview.ipynb](overview.ipynb) shows the screening summary, the five figures and the method. [FINDINGS.md](FINDINGS.md) is the written report.

## Run

```bash
uv sync --locked --extra ecg
```

```bash
uv run python analysis/ecg/scripts/ecg_eda.py --data-dir <folder with ECG .tsv(.gz) and .json files>
```

The ECG files come from the LEMON physiology folder (`Continuous_Peripheral_Physiology_During_MRI_MPILMBB_LEMON/MRI_PERPHYS_joined/`). Per-person outputs go to `data/derived/ecg/`, which is not in Git. Re-running the whole analysis inside the notebook is also possible: set `RUN_ANALYSIS = True` and `DATA_DIR` in its last cell.

## Outputs

| File | What |
|---|---|
| `results/aggregate_summary.json` | Group counts: targeted, readable, complete, duration and trigger checks |
| `results/methods.json` | Settings and thresholds used |
| `figures/01-05_*.png` | Coverage and recording structure, signal and detection diagnostics, duration ECDF, amplitude variability, candidate intervals |
| `FINDINGS.md` | Written summary: coverage, what was measured, review flags, next steps |

## Main results

- **Coverage:** 206 ECG recordings were targeted, out of the 213 listed. These are the people with ECG, rs-fMRI and PSQ. All 206 were fully read, and automatic beat detection ran on all of them.
- **Review flags** (flags overlap; they are not exclusions):
  - 197 have abrupt changes in the interval between beats;
  - 59 have candidate beat intervals outside 300-2000 ms;
  - 14 do not have 657 scanner triggers;
  - 11 are not 919.8 s long;
  - 15 had no beats detected in the first 60 s.
- **Scan match:** for 201 people, the same-run fMRI file was verified. For the other 5 this must be resolved before any combined ECG-fMRI analysis.

## Open questions and caveats

- **Day-1 ECG column:** the Day-1 availability table has an `ECG` column that no LEMON info file defines. The follow-up table names ECG, blood pressure, pulse and respiration runs after rs-fMRI runs 1-4.
- **From the data paper** (Babayan et al. 2019): 1000 Hz for about 15.5 min during the resting scan, synchronised by scanner triggers, released as raw data without peak detection.
- **Conflicting source details:** the Mendes study is dated 2017 in one LEMON file and 2018 in another, and its sample size differs between sources (91 vs 194 vs 109).
- **Before HRV:** manual review of traces, reference beat annotations, a fixed analysis window, and alignment with the scan (see [`../respiration`](../respiration/README.md) for the trigger timing).
