# Stress questionnaires (PSQ and TICS)

This folder documents and cleans the two LEMON stress questionnaires, the Perceived Stress Questionnaire (PSQ) and the Trier Inventory for Chronic Stress (TICS), and then tests how their scores are built. Only questionnaire data is used.

**See the results:** [overview.ipynb](overview.ipynb) shows the checks and their answers, the score distributions, the agreement between PSQ and TICS, and younger vs older. It shows group-level numbers only.

## Run

```bash
uv run python analysis/stress_questionnaires/scripts/clean_stress.py
```

```bash
uv run python analysis/stress_questionnaires/scripts/psq_eda.py
```

1. **`clean_stress.py`:** checks, the clean table and the score-formula tests.
2. **`psq_eda.py`:** a teammate's descriptive PSQ analysis (distributions, quartiles, correlations).

Both read `data/LEMON/` and never change it. Each takes a few seconds.

## Outputs

| File | In Git? | Content |
|---|---|---|
| `results/score_checks.csv` | yes | Every check in one line: what was tested, the result, the conclusion |
| `results/score_descriptives.csv` | yes | n, missing, mean, SD, range, skew and extreme values for every score, for everyone, younger and older |
| `results/PSQ_summary_statistics.csv` | yes | PSQ subscales and total: N, missing, mean, SD, quartiles, IQR, range, values outside 1.5 IQR |
| `results/PSQ_pearson_correlations.csv`, `PSQ_spearman_correlations.csv` | yes | Correlations between the four subscales and the total (220 complete participants) |
| `figures/histograms_main_scores.png` | yes | Distribution of PSQ_OverallScore and TICS_ScreeningScale |
| `figures/01-04_PSQ_*.png` | yes | PSQ box plots, histograms with quartiles, total-score ECDF, correlation heatmaps |
| `data/derived/stress_questionnaires/psq_eda/` | no | `analysis.json` (contains IDs) and `correlations.json` |
| `data/derived/stress_questionnaires/stress_clean.csv` | no (participant data) | 227 rows of PSQ and TICS as numbers. No rows dropped, nothing imputed |
| `data/derived/stress_questionnaires/task2_checks.json` | no | Raw-text checks, ID checks, descriptives, outliers, score tests, correlations |
| `data/derived/stress_questionnaires/followup_checks.json` and `followup_test1_rows.csv` | no | PSQ formula test and the sensitivity check |
| `data/derived/stress_questionnaires/task2_report.md` and `followup_report.md` | no | Written reports. They name individual participants, so they stay out of Git |

## Main results

- **Coverage:** PSQ and TICS each have 227 rows. 220 participants have complete scores. Every ID matches the META file.
- **PSQ overall score:** it equals the mean of Worries, Tension, Demands and (100 − Joy) in all 220 complete rows. It is *not* the plain mean of the four subscales.
- **TICS:** the file has no total column. `TICS_ScreeningScale` is not the sum of the nine subscales; it equals the sum in 0 of 220 rows.
- **PSQ vs TICS:** PSQ_OverallScore correlates with TICS_ScreeningScale at Pearson r = 0.76 (n = 220). Leaving out the most extreme TICS value barely changes r.
- **PSQ distribution:**
  - The total score has mean 30.1 (SD 15.5), median 26.7, IQR 20-40 and range 0-75, with a tail towards high stress.
  - Joy is in the opposite direction to the other subscales: higher Joy means *less* stress.
  - Joy correlates with the total at r = −0.73. Worries, Tension and Demands correlate with it at 0.84, 0.90 and 0.79.
  - These correlations are partly built in, because the total is computed from the subscales.
- **Not confirmed:** the official scoring manuals (Levenstein 1993; Schulz & Schlotz 1999) could not be read, so these formulas are inferred from the data.

## Reproducibility

`scripts/clean_stress.py` replaces the original two scripts, which are kept unchanged in a local `archive/` folder (not on GitHub). It was checked against the original outputs:

- `stress_clean.csv` and `followup_test1_rows.csv` are byte-identical.
- `task2_checks.json` is identical.
- `followup_checks.json` differs only in the recorded input path.
- The histogram shows the same data; only the font rendering differs between machines.

`scripts/psq_eda.py` is the teammate's script with only the input and output folders changed. Their original package (code, notebook, notes) is kept unchanged in the local `archive/` folder (not on GitHub). Run here, it reproduces their tables exactly: the summary statistics and Spearman tables are byte-identical, and the Pearson table differs by at most 1e-15.
