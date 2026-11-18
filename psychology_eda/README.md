# LEMON PSQ analysis and participant matching

## What to show in class

1. **Read the scores.** `lemon_psychology_eda.py` loads the published PSQ table. A valid score is a finite number from 0 to 100.
2. **Describe the scores.** The same script counts missing scores and summarizes the distributions. `lemon_psq_plots.py` turns these patterns into six figures.
3. **Match participants.** `lemon_multimodal_cohort.py` finds the IDs that have a valid PSQ total, at least one resting fMRI file, and a complete resting EEG file set in the archive inventory.
4. **Check live access.** `lemon_live_check.py` requests the first byte of the required fMRI and EEG files. An ID enters the live CSV only when all three criteria pass.

## PSQ scores

The Perceived Stress Questionnaire asks people how much stress they perceive. LEMON used the 20-item German short form with a two-year reference period. Each item uses a 1–4 response scale. `PSQ.csv` contains the participant ID and the five published scores on a 0–100 scale. [LEMON data paper](https://doi.org/10.1038/sdata.2018.308) · [PSQ short form validation](https://doi.org/10.1097/01.psy.0000151491.80178.78)

| Column | Higher scores indicate |
| --- | --- |
| `PSQ_OverallScore` | More perceived stress |
| `PSQ_Worries` | More worry |
| `PSQ_Tension` | More tension |
| `PSQ_Joy` | More joy |
| `PSQ_Demands` | More perceived external demands |

The published total is used directly. Across all 220 complete rows, it matched the formula below within rounding error. The figures show Joy in its original direction.

```text
Total = (Worries + Tension + (100 − Joy) + Demands) / 4
```

- All five scores were available for **220 of 227 participants (96.9%)**. The other seven rows had no valid scores.
- The total score had a mean of **30.10**, a median of **26.67**, and a standard deviation of **15.47**. The observed range was **0–75**.
- The IQR rule flagged two total scores. Both were kept. The group summaries are descriptive, and Spearman correlations use participants with all four subscale scores.

## How the cohort is built

| Data | Inclusion rule |
| --- | --- |
| PSQ | Valid `PSQ_OverallScore` |
| fMRI | At least one nonempty resting-state BOLD file (`task-rest`, `.nii.gz` or `.nii`) |
| EEG | A complete raw EEG set (`.eeg`, `.vhdr`, `.vmrk`) or a complete preprocessed pair (`.set`, `.fdt`) for the same eyes-open or eyes-closed condition |

The November 5, 2026 GWDG inventory yielded **214 candidates** from 220 valid PSQ totals, 227 resting fMRI listings, and 215 eligible EEG file sets, counted by participant. Of the six participants with valid PSQ who were excluded, five lacked an eligible EEG set and one lacked resting fMRI. One of the EEG exclusions had a zero-byte marker file and no complete preprocessed pair. Among the 214 candidates, 213 had the raw EEG set and 201 had preprocessed pairs for both eye conditions. All 214 had the standard session-01, AP, run-01 BOLD file. [GWDG LEMON archive](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/)

The recordings are matched by participant ID. The LEMON protocol placed MRI on day one and EEG and psychological assessment on day two. The archive count describes file availability. A successful live check confirms first-byte access. Full downloads and signal quality checks are needed to determine the final analysis sample. [LEMON data paper](https://doi.org/10.1038/sdata.2018.308)

## Run from the project root

Use Python 3.12. If the LEMON source tables and archive inventory are already under `data/lemon/source/`, skip the fetch command.

```bash
uv sync --locked
uv run --locked python scripts/fetch_lemon.py --inventory-all
uv run --locked python -m psychology_eda.lemon_psychology_eda
uv run --locked python -m psychology_eda.lemon_psq_plots
uv run --locked python -m psychology_eda.lemon_multimodal_cohort
```

Run the live access check with a network connection to GWDG:

```bash
uv run --locked python -m psychology_eda.lemon_live_check
```

For valid PSQ scores, the live check requires HTTP 206 and one readable byte from a BOLD file and every file in an eligible EEG set. The full signal files are never saved by this check. In the report, `not_checked` indicates no valid PSQ total, `not_listed` indicates no suitable file or complete set in the inventory, and `unverified` indicates that the live check did not pass for any listed option.

| Output | Contents |
| --- | --- |
| `outputs/lemon/psychology/PSQ.csv` | Original published scores |
| `outputs/lemon/psychology/psq_descriptives.csv` | Overall, age-group, and recorded-gender summaries |
| `outputs/lemon/psychology/psq_overall_distribution.csv` | Total scores grouped into ten-point intervals |
| `outputs/lemon/psychology_figures/` | Total and subscale distributions, age and gender box plots, Spearman correlations, and score availability |
| `outputs/lemon/multimodal/psq_fmri_eeg_subjects.csv` | IDs that meet all three archive criteria |
| `outputs/lemon/multimodal/psq_fmri_eeg_evidence.csv` | Scores, file paths, and inclusion decisions |
| `outputs/lemon/multimodal/psq_fmri_eeg_live_check.csv` | Live access result for each ID |
| `outputs/lemon/multimodal/psq_fmri_eeg_live_verified_subjects.csv` | IDs that passed all three live criteria |
| `outputs/lemon/psychology_other/questionnaire_coverage.csv` | Coverage of 23 questionnaire tables |

In the coverage table, `any_score_n` counts IDs with at least one observed score and `complete_score_n` counts IDs with every score observed. For PSQ, scores must be finite and in range. For other questionnaires, nonempty values count after missing-value placeholders are removed.

## Earlier ECG comparison

`uv run --locked python -m psychology_eda.lemon_cohort_eda` reproduces the earlier PSQ, fMRI, and ECG comparison. It matches the resting BOLD and ECG files from the same session-01, AP, run-01 scan among the 227 demographic IDs. It found 226 BOLD listings, 213 ECG listings, and 212 BOLD–ECG pairs. Of these, 206 also had a valid PSQ total and both JSON sidecars. This count is based on file listings. The outputs are `psq_bold_ecg_cohorts.csv` and `psq_bold_ecg_candidates.csv` under `outputs/lemon/psychology_other/`.

The source tables and generated outputs are excluded from Git. The scripts, environment files, and fetch command let project members reproduce them locally.
