# LEMON respiration EDA

This analysis covers the session 01 AP run 01 respiration recordings. It checks signal quality and fMRI trigger timing, estimates breathing rate by two methods, and reports coverage of the ECG–PSQ–BOLD candidate cohort. Quality flags were computed without PSQ scores or HRV values.

## Main findings

- **Coverage:** 156 of 206 candidates have respiration data. Coverage was 39/69 among women and 117/137 among men.
- **Rate:** All 163 recordings had finite respiration and trigger samples. The median Welch estimate was 16.53 breaths/min. The median absolute difference from the peak interval estimate was 0.38 breaths/min. Twenty-one of 156 matched recordings had low band power or a sensitive rate estimate.
- **Timing:** Every trigger interval was exactly 1,400 samples at 1,000 Hz. Among the 156 matched recordings, 54 had one possible 657-trigger window, 100 had multiple possible windows, and two had none. Only 45 had a unique window and neither signal flag. Verify the actual BOLD start and volume count before generating regressors. This EDA did not align or denoise fMRI.

## Run

Use Python 3.12. Supply the [GWDG respiration TSV/JSON pairs and META demographics CSV](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/) and a candidate ID list. If the list is missing, follow the [PSQ data setup](../psychology_eda/README.md#run-from-the-project-root) and run the cohort script below.

```sh
uv sync --locked
uv run --locked python -m psychology_eda.lemon_cohort_eda
uv run --locked python -m respiration_eda.lemon_respiration_eda \
  --data /path/to/respiration \
  --base outputs/lemon/psychology_other/psq_bold_ecg_candidates.csv \
  --demographics /path/to/META.csv \
  --output outputs/lemon/respiration_eda
```

| Output | Contents |
|---|---|
| [respiration_figures/](../outputs/lemon/respiration_figures/) | Eight standalone PNGs for coverage, timing, quality, rate agreement, within-recording variation, examples, sensitivity, and correlations |
| [participant_eda.csv](../outputs/lemon/respiration_eda/participant_eda.csv) | Participant coverage, raw signal checks, timing, rate estimates, and flags |
| [cohort_coverage.csv](../outputs/lemon/respiration_eda/cohort_coverage.csv) | Coverage by age and recorded gender with 95% Wilson intervals |
| [minute_windows.csv](../outputs/lemon/respiration_eda/minute_windows.csv) | Rates and spectral metrics for 2,515 full, nonoverlapping 60-second windows |
| `recording_qc/` | One PNG per recording when `--recording-plots` is supplied |

The published tables are snapshots of the EDA run. Individual QC plots are generated locally. Rates are exploratory estimates in the 0.10–0.60 Hz band. Timing flags use a 1.4 s interval with a 50 ms tolerance. Signal flags use a 50% band power threshold (whole recording or at least 25% of full minutes) and a 3 breaths/min method or peak-setting difference. These are review flags, not automatic exclusions.

The correlation figure reports Pearson and Spearman coefficients for the two breathing-rate estimates, first-eight-minute versus full-recording estimates, and duration versus scanner trigger count. The full recording includes the first eight minutes.
