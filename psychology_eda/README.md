# LEMON PSQ analysis and participant matching

## PSQ EDA notebook

Open [PSQ_EDA.ipynb](PSQ_EDA.ipynb), select the project's Python 3.12 environment, and run all cells. The notebook calls [psq_eda.py](psq_eda.py) using `outputs/lemon/psychology/PSQ.csv`. It displays four figures and saves them under `outputs/lemon/psychology/standalone/figures/`.

| Figure | Contents |
| --- | --- |
| `01_PSQ_boxplots.png` | Total and subscale box plots with individual observations |
| `02_PSQ_distributions.png` | Histograms with medians and interquartile ranges |
| `03_PSQ_total_ECDF.png` | Empirical cumulative distribution of the total score |
| `04_PSQ_correlations.png` | Pearson and Spearman heatmaps for the subscales and total score |

The same results folder contains summary statistics and both correlation matrices as CSVs. With the LEMON demographics CSV available, the notebook also displays the six original project figures and saves them under `outputs/lemon/psychology/standalone/project_figures/`.

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
- The IQR rule flagged two total scores. Both were kept. The group summaries are descriptive. The notebook computes correlations using participants with all five scores.

## Run from the project root

Use Python 3.12. These commands expect the LEMON source tables under `data/lemon/source/`.

```bash
uv sync --locked
uv run --locked python -m psychology_eda.lemon_psychology_eda
```

| Output | Contents |
| --- | --- |
| `outputs/lemon/psychology/PSQ.csv` | Original published scores |
| `outputs/lemon/psychology/psq_descriptives.csv` | Overall, age-group, and recorded-gender summaries |
| `outputs/lemon/psychology/psq_overall_distribution.csv` | Total scores grouped into ten-point intervals |
| `outputs/lemon/psychology/standalone/project_figures/` | Six original PSQ figures, including age, gender, and score availability |
| `outputs/lemon/psychology_other/questionnaire_coverage.csv` | Coverage of 23 questionnaire tables |

In the coverage table, `any_score_n` counts IDs with at least one observed score and `complete_score_n` counts IDs with every score observed. For PSQ, scores must be finite and in range. For other questionnaires, nonempty values count after missing-value placeholders are removed.

## PSQ, fMRI, and ECG cohort

The respiration analysis uses an existing candidate CSV. The archive inventory yielded 226 BOLD listings, 213 ECG listings, and 212 pairs matched to the same session-01, AP, run-01 scan among the 227 demographic IDs. Of those pairs, 206 had a valid PSQ total and both JSON sidecars. See the [respiration input requirements](../respiration_eda/README.md#run) to rerun the analysis.
