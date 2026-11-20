# ECG and physiology

**Status: documentation only.** No signal has been opened or analysed. The physiology recordings (`Continuous_Peripheral_Physiology_During_MRI`) are not in the local copy of LEMON yet.

## What the documentation says

- **LEMON info files.**
  - The follow-up availability table names ECG, blood pressure (BPP), pulse (PPG) and respiration runs. Each run is tied by name to rs-fMRI runs 1-4.
  - The Day-1 table has an `ECG` column, but no info file defines it.
- **The data paper** (Babayan et al. 2019; read through a tool summary, not checked against the PDF):
  - signals: beat-to-beat blood pressure, ECG, pulse and respiration;
  - sampling and length: 1000 Hz for 15.5 min, during the resting-state scan;
  - synchronisation: a trigger links the recording to the fMRI volumes;
  - release: raw data only, with no peak detection.
- **One physiology file is on the laptop** (`data/LEMON/sub-032301.tar.gz`). It confirms the scanner triggers: 657 pulses, 1.4 s apart (see `fmri_eda`, check A3).
- **Counts:** how many people are listed with ECG, and how that overlaps with rs-fMRI and PSQ, is in [`../participant_table/results/availability_counts.csv`](../participant_table/results/availability_counts.csv). ECG: 213 people; ECG and rs-fMRI: 212.

## Open questions before any analysis

1. What does the Day-1 `ECG` flag mean? Are the follow-up runs the same recordings as the paper's MRI-session data?
2. What are the file format, channel names, units and exact recording window?
3. **Conflicts in the sources:**
   - the Mendes study is dated 2017 in one LEMON file and 2018 in another;
   - its sample size differs between sources (91 vs 194 vs 109 people).

**Next step:** download the physiology folder's info files and file list into `data/LEMON/`, plus the paper PDF.

The full phase-0 notes, with exact file paths and quotes, are kept in the local `archive/` folder (not on GitHub).
