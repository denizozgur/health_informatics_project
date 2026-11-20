# Dataset overview (whole LEMON archive)

These are a teammate's dataset-wide checks, done before choosing a research question. They cover what the archive contains, how the tables relate to each other, and what one participant's raw MRI, EEG and physiology files look like. The research question these checks led to is in [`docs/lemon_research_proposal.md`](../../docs/lemon_research_proposal.md).

| Script | What it does |
|---|---|
| `scripts/lemon_eda.py` | Joins all behavioural, medical and cognitive tables into one participant table. It reports source-table quality, descriptives, outliers, biomarker-cognition correlations, age-group comparisons, modality overlap, and archive file and format counts |
| `scripts/lemon_pilot.py` | Inspects one participant's resting-state run (fMRI, ECG, respiration, PSQ) before any HRV or fMRI features are computed |
| `scripts/lemon_visual_inspection.py` | Plots example MRI sequences (slices, intensities) and EEG signals and spectra for a small downloaded subset |

## Run

The scripts expect the archive mirror created by [`data_download/`](../../data_download/README.md), under `data/lemon/source/` and `data/lemon/subset/`.

```bash
uv run python analysis/dataset_overview/scripts/lemon_eda.py
```

```bash
uv run python analysis/dataset_overview/scripts/lemon_visual_inspection.py
```

```bash
uv run python analysis/dataset_overview/scripts/lemon_pilot.py --help
```

All outputs go to `data/derived/dataset_overview/` (not in Git). They include a participant-level master table, so nothing from them is committed. The findings are summarised in the documents under `docs/`.

**Not re-run after the move.** The archive mirror is not on this laptop. The only code change was the output folder and the project-root path, so the scripts should behave as before. Run them once where the mirror exists to confirm.
