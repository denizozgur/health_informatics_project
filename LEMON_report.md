# LEMON dataset: short report

## Installation status

The LEMON behavioral data is already on this machine in `data/LEMON/`, so nothing was downloaded. It contains:

- `Cognitive_Test_Battery_LEMON/`: CVLT, LPS, RWT, TAP (alertness, incompatibility, working memory), TMT, WST
- `Emotion_and_Personality_Test_Battery_LEMON/`: questionnaires such as BISBAS, CERQ, COPE, ERQ, MARS, NEO-FFI, PSQ, STAI, STAXI, TAS, TEIQue-SF, UPPS, YFAS
- `Medical_LEMON/`: anthropometry, blood pressure, blood sample, dates
- `Data_Availability_Tables/`: Day 1, Day 2, and follow-up availability CSVs
- `META_File_IDs_Age_Gender_Education_Drug_Smoke_SKID_LEMON.csv`: one row per participant, with its `_INFO` description file

I could not run `uv sync --locked` or check `.venv`, because this session has no shell on your computer. Run `uv sync --locked` in the project folder yourself to confirm the environment.

## What the data is

LEMON (MPI-Leipzig Mind-Brain-Body) is a multimodal study of healthy adults. It combines MRI, EEG, behavioral tests, questionnaires, and physiology. The original paper is Babayan et al. (2019), Scientific Data, doi:10.1038/sdata.2018.308, and it describes 227 participants.

## The meta file

- **Rows:** 228 participants, with IDs in BIDS form (`sub-0100xx`, `sub-0102xx`, and so on).
- **Gender:** coded 1 = female, 2 = male.
- **Age:** given in 5-year bins, from 20–25 up to 75–80. Younger adults (roughly 20–35) and older adults (roughly 55–80) are both present.
- **Education, handedness, smoking:** school type (Gymnasium, Realschule, Hauptschule, and others), handedness, and smoking status (non-smoker, occasional smoker, smoker).
- **Drug screen:** urine test on Day 2, with results such as THC, BZO, and MOP.
- **Clinical:** SKID diagnoses (DSM-IV), plus AUDIT, Hamilton scale, and BSL-23 scores for some participants.
- **Missing data:** a number of rows have blank fields, and some diagnosis fields are free text, so they need cleaning before analysis.

## Caveats

- I read the meta file directly and did not run a script, so I have not computed exact counts by gender or age bin. Treat the figures above as approximate.
- The test batteries are one CSV per instrument, each with an `_info` file. Read the `_info` file before interpreting any variable.
- Participant overlap across instruments is not yet checked. Per the project README, do not assume every participant has every measurement.
- Keep the originals unchanged and do not commit participant data to Git.

## Suggested next steps

1. Run `uv sync --locked` and confirm imports in the notebook.
2. Count participants per instrument and per age group with pandas.
3. Decide the first target, such as cognitive scores or the EEG subset, and check overlap before modelling.
