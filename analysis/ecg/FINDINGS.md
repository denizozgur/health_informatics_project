# ECG cohort exploratory analysis
Date: 19 November 2026

## Coverage
Target: 206 main-session ECG records selected from a broader screen of 213 (227 main-cohort participants overall).
Processed: 206. Fully read: 206. Automatic detection completed: 206.
Not yet processed: 0. Read/processing errors: 0.
These counts describe automatic screening, not validated ECG suitability.

## What was measured
Full numeric read (and CRC for gzip inputs), sampling frequency, rows, duration, finite values, amplitude MAD and extremes, constant runs, scanner-trigger counts and spacing. NeuroKit cleaning/detection was run on full finite signals; independently cleaned NeuroKit and Engzee pipelines were compared on the first 60 seconds, both without automatic artifact correction. Individual inspection plots and candidate peak arrays are retained under private/.

## Important distinction
No participant was declared finally usable by this script. No normal-beat reference labels were supplied; no validated RMSSD or PSQ associations were calculated. Numeric PSQ values were not used. A comparison between algorithms is not a detection accuracy estimate. Absence of a listed review flag does not prove a clean recording.

## Review flags (not exclusion criteria)
Constant runs >=1 s; nonfinite values; extreme amplitudes beyond 20 x 1.4826 x MAD from the median for >=1 s; candidate intervals outside 300-2000 ms; successive interval ratios outside [0.5, 2]; unexpected duration/trigger counts or median trigger spacing. These exploratory thresholds are documented before outcome analysis but require methodological review before use as eligibility rules.

Exact same-run MNI header verified in 201 requested participants; not verified in 5. This does not prevent ECG-only EDA but requires resolution before a combined fMRI analysis.

Flag counts (overlapping):
- abrupt_candidate_interval_ratio: 197
- sustained_extreme_amplitude: 5
- trigger_count_not_657: 14
- duration_not_919p8s: 11
- candidate_interval_outside_300_2000ms: 59
- detector_empty_first60: 15
- constant_run_ge_1s: 1

## Next required work
Manual review of full traces and prespecified windows, reference beat annotations or reviewed corrections, fixed analysis-segment selection, and same-scan alignment/respiration QC for the physiology test. The previous 12-person visual pilot remains a separate review; this automatic cohort scan does not replace it.

## Sources
- Babayan et al. (2019), LEMON descriptor: https://doi.org/10.1038/sdata.2018.308
- Official ECG files: https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/Continuous_Peripheral_Physiology_During_MRI_MPILMBB_LEMON/MRI_PERPHYS_joined/
- NeuroKit2 documentation: https://neuropsychology.github.io/NeuroKit/
- Prior participant/file inventory and main-session JSON sidecars audited on 19 November 2026.
