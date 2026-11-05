# Research project: team work guide

## Shared starting point

Our aim is to investigate imaging patterns associated with Parkinson's disease and cognitive impairment, and eventually assess whether model explanations have a plausible biological interpretation. These are exploratory research questions; predictive associations and explanations alone do not establish causation or clinical usefulness.

1. Follow [README.md](README.md) to create the Python 3.12 environment, download ds005892, and select `.venv` as the VS Code notebook kernel. The dataset is already downloaded on the machine where this repository was prepared; other team members need their own copy.
2. Work from the project root so paths such as `ds005892/participants.tsv` resolve consistently. Read the dataset's own `README`, `dataset_description.json`, and JSON sidecars before making assumptions. Record the dataset version/DOI and any data exclusions in your work.
3. The current participant table has `participant_id`, `group`, `age`, and `sex`. The accompanying JSON describes the groups HC, PD-NC and PD-MCI. Verify the actual values and missingness; do not assume other clinical scores are available. The metadata describes the `sex` field as gender, so report this ambiguity instead of assuming how it was measured.
4. The dataset contains anatomical (`anat`), functional (`func`), and field-map (`fmap`) files; inspect each participant rather than assuming their files are identical. NIfTI images are `.nii.gz`, with accompanying JSON metadata.
5. Keep source data unchanged and out of Git. Do not commit participant-level data, generated datasets, or large outputs. Agree with the group lead before sharing participant-level tables, split files, or images; even public data should be handled thoughtfully. Record commands, software versions, assumptions, and decisions so work can be reproduced.
6. The existing environment covers basic exploration, not CNN training or a complete neuroimaging preprocessing pipeline. Propose additional tools when needed and follow [AGENTS.md](AGENTS.md) to add only justified dependencies. Coordinate dependency changes with the team.

## Yekta — dataset analysis and statistics

### Work sequence

1. Download or verify the dataset using the README. List participant folders and compare their identifiers with `participants.tsv`; report duplicates, unmatched identifiers, and missing values without silently dropping records.
2. Build an inventory per participant and modality: count scans by meaningful BIDS suffix (such as `T1w` and `bold`), and distinguish field maps and JSON sidecars from scans used as model inputs. Record missing files and unexpected naming patterns. Summarize counts by group.
3. Use NiBabel to inspect image shape, voxel sizes, and affine/orientation; for 4D BOLD data record the number of time points. Read TR from the appropriate JSON sidecar and record units and missing or inconsistent values. Images and metadata may differ between participants, so inspect all files rather than extrapolating from one scan.
4. Summarize group sizes, missingness, age distributions, and sex categories overall and by group. Present counts alongside percentages and descriptive statistics. Identify imbalance and variables that may confound interpretation.
5. Explore relationships among available numerical variables, reporting sample sizes and missing-value handling. Compare age and sex distributions across groups with suitable methods and clearly stated assumptions; where expected counts are small, use an appropriate alternative or report descriptive results. Treat tests and correlations as exploratory, avoid causal claims, and note multiple comparisons and small-sample limitations.
6. Share a concise list of data-quality concerns and variables worth considering with Burak and the group lead before modelling decisions are fixed.

### Notebook starting point

```python
from pathlib import Path
import pandas as pd
import nibabel as nib

root = Path('ds005892')
participants = pd.read_csv(root / 'participants.tsv', sep='\t')
print(participants.columns.tolist())
print(participants['group'].value_counts(dropna=False))

example = root / 'sub-MJF001' / 'anat' / 'sub-MJF001_T1w.nii.gz'
image = nib.load(example)
print('shape:', image.shape, 'voxel sizes (mm):', image.header.get_zooms()[:3])
```

### Deliverables

- Dataset inventory and a reproducible statistical exploration notebook.
- Group distribution plots and, where meaningful, correlation matrices with readable labels and sample sizes.
- A short summary of missingness, inconsistencies, potential confounders, and modelling-relevant variables. Avoid placing participant-level exports in Git.

## Burak — imaging exploration and baseline CNN

### Part A: understand the images

1. Read the inventory and inspect representative T1w, resting-state BOLD, and associated JSON files. Explain that T1w generally provides anatomical contrast, while resting-state BOLD is a time series used to study functional activity/connectivity. Describe actual dimensions, voxel sizes, orientation and BOLD time points from this dataset.
2. Plot clearly labelled slices from representative scans across available groups. Explain slice orientation, intensity scaling, and that a 4D BOLD image needs an explicitly chosen time point or summary. Use appropriate privacy and sharing judgment for identifiable-looking anatomical images.
3. Identify preprocessing needs and limitations: image orientation, quality control, registration, intensity normalization, skull stripping and, for fMRI, motion/distortion correction and temporal processing as appropriate. Check available metadata before promising any particular correction. Document tools and decisions rather than assuming raw images are analysis-ready.

### Part B: reliable baseline

1. With the lead, define the prediction target, modality and unit of observation. Three-class HC/PD-NC/PD-MCI is the preferred starting question if group sizes support a meaningful evaluation; document any change and why. Begin with a tractable input representation and a simple CNN; make the choice of 2D, 3D or fMRI representation explicit.
2. Assign train, validation and test partitions **by participant** before fitting preprocessing or feature selection. Keep every scan, slice and time point from the same participant in one partition. Use a documented random seed, inspect class counts in each split, and maintain the split mapping locally. Agree on a fixed split with the group lead before model comparisons.
3. Fit learned preprocessing and normalization on training participants only, then apply the fitted operations to validation and test participants. Use training data for fitting and validation data for model selection; reserve the test set for final evaluation after choices are fixed. Avoid repeatedly tuning against test results.
4. Establish a simple non-deep-learning comparator if feasible, using the same participant splits and an appropriate training-only feature pipeline. The provided environment does not yet include a deep-learning framework or scikit-learn; agree on the necessary packages and use the project's `uv` procedure.
5. Report participant-level accuracy, balanced accuracy, macro-F1, confusion matrix, class support, and per-class precision and recall. If multiple predictions are produced per participant, specify how they are combined before evaluating. Record hardware, software versions, seed, splits, preprocessing, training settings, and limitations. Small or imbalanced test groups make estimates uncertain; report counts and avoid claims based on an arbitrary accuracy target.

### Deliverables

- Imaging notes with labelled visualizations and quality-control observations.
- Reproducible preprocessing and baseline code, with documented inputs, outputs and dependencies.
- A results report including the split protocol, metrics, comparator if feasible, and limitations. Keep raw data and large/generated artifacts out of Git.

## Melis and Elif — neuroscience and literature review

Coordinate your division of papers and record who reviewed each one. Both of you should review the integrated region/network table before sharing it; the following split is a suggested starting point and can be adjusted together.

### Melis — disease mechanisms and structural imaging

1. Review Parkinson's disease mechanisms relevant to motor and cognitive symptoms, and the neural systems implicated in cognitive impairment.
2. Review structural MRI findings, including regional volume and cortical thickness where the paper actually measures them. Record populations, methods, comparisons and limitations.
3. Summarize evidence on age and sex or gender differences, distinguishing the terms and definitions used in each study.

### Elif — cognition and functional imaging

1. Review brain regions and networks relevant to memory, attention and executive function, including their relevance to Parkinson's cognitive impairment.
2. Review resting-state fMRI studies of activity and functional connectivity, noting the networks, preprocessing, motion handling and direction of observed effects.
3. Find similar datasets and prediction/XAI studies; note whether they use comparable participants, labels, imaging inputs and validation methods.

### Shared evidence workflow

- Search sources such as PubMed and the references cited by relevant reviews, then prioritize original peer-reviewed studies. Record the database, search terms, date, inclusion criteria, and any important contradictory results.
- For every substantive finding, fill one row of the table below. Cite a DOI or stable accessible link and distinguish original findings from review summaries. Do not describe an association as a proven mechanism. Mark evidence strength as your assessment and explain uncertainty or disagreement.
- Separately propose questions that could be explored with imaging or XAI in this dataset. Check with Yekta and Burak that a proposed measure can actually be obtained; region-level claims require an appropriate mapping from model inputs to anatomy.

| Finding or question | Region/network and function | Measure and observed direction | Population and comparison | Source and DOI/link | Evidence and limitations | Relevance to our data |
| --- | --- | --- | --- | --- | --- | --- |
| Add finding | Add region and function | Add actual measure and result | Add sample and groups | Add citation | Add uncertainty | Add feasible next step |

### Deliverables

- A biological background document and cited literature review.
- A shared table linking regions, functions and evidence for Parkinson's disease and cognitive impairment, including inconsistent findings.
- A shortlist of biologically motivated, feasible questions for later XAI investigation.

## Group lead — research direction and integration

1. Gather Yekta's inventory and limitations, Burak's imaging and baseline proposal, and Melis and Elif's evidence table. Identify where the dataset can and cannot address proposed questions.
2. Agree on the initial target, modality, participant-level split and evaluation plan before the baseline is trained. Consider class sizes, confounders, preprocessing feasibility, and whether external validation is available. Keep the final test set reserved.
3. Decide whether imaging-derived tabular features and a simple comparator are feasible without leakage. Define how all approaches will use the same participant partitions.
4. Review the literature to formulate a specific contribution beyond an accuracy claim. Document the research question, hypotheses, assumptions, decisions, and unresolved risks.
5. Select XAI methods only after the model and inputs are understood. Plan sanity checks, stability tests, and comparisons with literature; explanations can be misleading and do not independently establish biological mechanisms.
6. Integrate the results into a report with dataset provenance, methods, metrics, limitations, and next steps. Coordinate what can be shared or committed, keeping data and large outputs outside Git.

## Coordination checkpoints

1. **Data check:** Yekta reports group counts, availability and inconsistencies; Burak confirms usable image inputs.
2. **Research check:** Melis and Elif present the evidence table and candidate hypotheses; the lead checks them against actual available data.
3. **Experiment agreement:** The team records target, modality, participant split, preprocessing and metrics before model fitting.
4. **Review:** Burak presents the baseline and limitations; the team identifies defensible next steps and whether XAI is appropriate.
