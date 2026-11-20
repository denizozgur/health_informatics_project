# Health informatics project: LEMON stress, heart and brain data

We study how **perceived stress** relates to **heart** and **brain** measures in healthy adults. The data is the open **LEMON** dataset (MPI Leipzig Mind-Brain-Body). It has 227 participants, roughly half aged 20-40 and the rest 55-80, each with questionnaires, medical data, MRI, EEG and physiology ([Babayan et al. 2019](https://doi.org/10.1038/sdata.2018.308)).

This README is the walkthrough: what we did, in what order, where each result is, and how to reproduce it.

## 1. Set up

You need Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/). From the project folder:

```bash
uv sync --locked
```

This creates `.venv` with the exact package versions in `uv.lock`. To open the notebooks in VS Code, choose that `.venv` as the kernel. Add packages with `uv add <package>` (never `pip install`), and commit `pyproject.toml` and `uv.lock` together.

## 2. Get the data (not in Git)

Everything goes under `data/LEMON/`, which Git ignores and which no script ever changes. Source: the [public LEMON archive](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/).

| What | Where it goes | Needed for |
|---|---|---|
| Behavioural data: questionnaires, medical, META file, availability tables | `data/LEMON/` | participant table, stress questionnaires |
| Preprocessed resting-state fMRI, `*_MNI2mm.nii.gz` (~2.2 GB per person, ~500 GB in total) | `data/LEMON/MRI_MNI2mm/` | fMRI EDA |
| fMRI extras: confounds, `bold.json`, QC PDFs | `data/LEMON/MRI_extras/` | fMRI EDA |

To download the behavioural part (Linux, `wget`):

```bash
mkdir -p data/LEMON && wget -r -nc -np -nH --cut-dirs=4 -R 'index.html*' -P data/LEMON 'https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/Behavioural_Data_MPILMBB_LEMON/'
```

The fMRI files are too big for most laptops. The heavy fMRI step can run on Google Colab instead; see [analysis/fmri_eda/COLAB.md](analysis/fmri_eda/COLAB.md).

## 3. The analysis, step by step

Each task has its own folder in `analysis/`, and every folder has the same layout:

```
analysis/<task>/
  README.md        what the task does, how to run it, main results, open questions
  overview.ipynb   the results at a glance (already run, group-level only)
  scripts/         the code; run from the project root with `uv run python ...`
  results/         group-level tables (CSV), no participant IDs
  figures/         group-level figures
```

Anything with one row per participant is written to `data/derived/<task>/` instead, so it never enters Git.

### Step 1: Participant table → [analysis/participant_table](analysis/participant_table/README.md)

This step builds one row per participant from all the behavioural files, and records who has which data according to the LEMON availability tables.

- **Result:** 228 participants. 220 have both stress questionnaires, 213 are listed with ECG, 226 with rs-fMRI, and 206 with ECG, rs-fMRI and PSQ.
- **Open question:** several availability columns (the Day-1 ECG, for example) are not defined in the LEMON documentation.

### Step 2: Stress questionnaires → [analysis/stress_questionnaires](analysis/stress_questionnaires/README.md)

This step cleans the two stress questionnaires (PSQ and TICS) and works out how their scores are built.

- **PSQ:** the overall score is the mean of Worries, Tension, Demands and (100 − Joy).
- **TICS:** there is no total score, and its screening scale is not a sum of the subscales.
- **Agreement:** PSQ and TICS correlate strongly (r = 0.76).
- **PSQ descriptive analysis (from a teammate):**
  - quartiles, distributions and subscale correlations;
  - the PSQ total has median 26.7 and IQR 20-40;
  - Joy runs opposite to stress.

### Step 3: fMRI checks and exploration → [analysis/fmri_eda](analysis/fmri_eda/README.md)

Before building brain features, this step checks the preprocessed resting-state fMRI of 159 people.

- **Method:** 43 checks, each with a PASS / FAIL / INFO status. Key numbers are re-checked independently from the raw files (115 of 115 agree).
- **Findings:**
  - The real time between images is 1.4 s, although the file header says 1.0 s.
  - The signal is clean, z-scored and band-pass filtered.
  - Connectivity is person-specific: every person is identified from their own scan.
  - Older people move about twice as much, so motion must be controlled in any age comparison.
  - One scan has an unusual brain mask.
- **Details:** [FINDINGS.md](analysis/fmri_eda/FINDINGS.md) explains every failed check.

### Step 4: ECG during the scan → [analysis/ecg](analysis/ecg/README.md)

This step screens the ECG recorded during the fMRI, from a teammate.

- **Coverage:** 206 recordings, all fully read, with automatic beat detection on each.
- **Flags for review:** 197 have abrupt changes in beat intervals, 14 do not have 657 scanner triggers, and 11 have an unexpected length.
- **Not done yet:** no HRV is computed, and no recording is declared usable until the beats are reviewed by hand.

### Step 5: Respiration during the scan → [analysis/respiration](analysis/respiration/README.md)

This step checks breathing recordings and scanner-trigger timing, from a teammate.

- **Coverage:** 156 of the 206 ECG + fMRI + PSQ candidates have respiration data.
- **Breathing rate:** median 16.5 breaths/min.
- **Timing:** every trigger interval is exactly 1.4 s, which agrees with the fMRI TR found in step 3. For only 45 recordings is the scan's start position unique and the signal unflagged.

### Before the steps: dataset overview and research question

- [analysis/dataset_overview](analysis/dataset_overview/README.md): a teammate's checks across the whole archive (tables, overlap, example raw files).
- [`docs/`](docs/) holds the project documents:
  - [research proposal](docs/lemon_research_proposal.md): the recommended question and the planned comparisons;
  - [paper review](docs/lemon_paper_review.md): what the LEMON papers say about methods and caveats;
  - [biological background](docs/lemon_biological_background.md): what each measurement means biologically.
- [data_download](data_download/README.md): scripts that mirror the public archive.

### Reproduce everything

```bash
uv run python analysis/participant_table/scripts/build_master_table.py
```

```bash
uv run python analysis/participant_table/scripts/availability_flags.py
```

```bash
uv run python analysis/participant_table/scripts/data_dictionary.py
```

```bash
uv run python analysis/stress_questionnaires/scripts/clean_stress.py
```

```bash
uv run python analysis/stress_questionnaires/scripts/psq_eda.py
```

The fMRI steps are listed in [analysis/fmri_eda/README.md](analysis/fmri_eda/README.md). Each task README says how the code was checked: the participant-table and stress scripts regenerate the original outputs byte for byte.

## 4. Rules we follow

- **Raw data is read-only.** Nothing under `data/LEMON/` is modified.
- **No participant-level data in Git.** Only group-level tables, figures and code are committed. Figures label people by pseudonym or not at all.
- **Unknowns are marked, not guessed.** Anything the documentation does not settle is marked **unclear** and listed as an open question.
- **Old versions are kept locally.** Earlier scripts and reports are kept in a local `archive/` folder; it is not published.

## Repository map

```
README.md                 this walkthrough
analysis/                 one folder per task:
  dataset_overview/         whole-archive checks
  participant_table/        one row per participant, data availability
  stress_questionnaires/    PSQ and TICS
  fmri_eda/                 preprocessed resting-state fMRI
  ecg/                      ECG during the scan
  respiration/              breathing and trigger timing during the scan
docs/                     research proposal, paper review, biological background
data_download/            scripts to mirror the public LEMON archive
pyproject.toml, uv.lock   exact environment (ECG needs: uv sync --locked --extra ecg)
data/                     not in Git: raw LEMON data and data/derived/<task> (participant-level outputs)
```
