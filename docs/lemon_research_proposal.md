# Proposed multimodal cognition study

Status on 5 November 2026: recommendation for review, not an approved target, implemented model, or preregistration. Initial dataset and EDA findings are in the accompanying reports. No CNN training has started.

## Recommended question

**Do systemic metabolic measurements improve prediction of continuous Trail Making Test B completion time beyond demographics and imaging features in healthy younger and older LEMON participants?**

Use `TMT_5`, the raw TMT-B duration in seconds, as the provisional primary endpoint. All 227 canonical demographic participants have numeric values. The target has a clear unit, avoids an arbitrary impairment threshold, and concerns a task with executive, visual-search, and motor-speed demands. It is not a pure measure of one brain function, a dementia diagnosis, or longitudinal cognitive decline.

The hypothesis is that adding a small set of metabolic measurements may improve held-out prediction error. A null or adverse change is a valid result. The current adjusted EDA does **not** establish that the added measurements will help TMT-B prediction.

Select this endpoint for interpretability, availability, and scientific scope rather than its EDA significance. CVLT learning total has an adjusted exploratory association with HbA1c, but selecting it as primary because of that finding would create outcome-selection bias. It remains a biologically plausible secondary endpoint, clearly marked as exploratory.

## Candidate questions and feasibility

| Candidate | Available evidence and sample constraint | Recommendation |
|---|---|---|
| Continuous TMT-B prediction | 227 targets; 170 with listed T1 and complete seven-marker panel, before QC | Preferred provisional endpoint |
| CVLT learning or delayed recall | Actual task scores and strong biological motivation; some missingness; EDA already inspected | Secondary exploratory endpoint; do not switch primary to chase significance |
| Young versus older classification | Age-bin labels available; large unobserved middle-age interval; recruitment and sequence confounding | Engineering exercise only; weak primary test of multimodal biological value |
| Continuous exact-age prediction | Public ages are five-year bins and cohort has an age gap | Do not present as exact biological age estimation |
| ALPS or BOLD–CSF prediction | Derived labels not computed here; preprocessing, timing, masks, and QC unresolved | Later dedicated study, not the first model |
| Disease classification | No validated case–control disease label identified | Not supported |

## Proposed comparisons

Use identical participant eligibility, splits, and evaluation cases for every primary modality comparison. Otherwise apparent multimodal improvement could simply reflect a different cohort.

1. Demographic reference: age-bin categories, sex, and cleaned education category.
2. Demographics plus imaging: a small, prespecified set of anatomical features after validated extraction and QC; EEG features can form a separate secondary branch.
3. Demographics plus biomarkers: HbA1c on one scale, glucose, LDL, HDL, and triglycerides, with a limited physiological set if justified. Report a seven-marker sensitivity panel adding total cholesterol and eGFR; do not assume all seven are independently informative.
4. Demographics plus imaging plus biomarkers: the primary incremental-value comparison against model 2.

Recent alcohol use and BMI are candidate covariates whose roles must be specified before modeling. eGFR can encode age and sex by construction; compare results without it. Avoid duplicate HbA1c or hemoglobin scales, reference ranges, participant IDs, acquisition paths, diagnostic free text, and availability flags as automatic features. Feature extraction choices must precede model selection rather than being chosen from the full-cohort heatmap.

For a required CNN component, prefer a small architecture after data readiness: a few 3D convolution blocks with global pooling for harmonized brain volumes, or a small 2D network with participant-level aggregation if resource limits require it. Decide after skull stripping, registration, resolution, cropping, and coverage are reviewed. A 2D slice is not an independent observation. Do not start either implementation solely because raw files load successfully.

Start prediction with a mean/median reference and regularized linear regression on validated features. Compare a compact nonlinear baseline only with a small tuning budget. A CNN should earn its computational cost through the same held-out comparison. Feature fusion should remain simple; no Transformer is needed.

## Cohort and evaluation recommendation

The initial seven-marker cohort has 171 participants, of whom 170 have listed T1 MRI; that paired T1 cohort contains 114 younger and 56 older participants. Requiring recognized EO EEG as well reduces the overlap to 155. These are availability counts before QC, not guaranteed training sample sizes. A smaller prespecified biomarker panel may retain more participants; quantify its missingness before choosing complete-case versus training-only imputation.

A 70/15/15 split of 170 would provide only roughly 25–26 participants for each validation and test partition, with fewer after QC. A single test estimate would be unstable. Recommend a fixed 20% participant holdout and nested cross-validation confined to the remaining development participants, subject to final cohort size. This is a proposal requiring a target/evaluation decision; no split has been generated. If three explicit sets are required by the course, freeze a single stratified 70/15/15 allocation and accept its uncertainty rather than repeatedly trying seeds.

Use seed 42 for the eventual allocation and record the exact participant manifest before generating slices or EEG segments. Stratify age group where feasible; check sex balance without repeatedly optimizing the split. Every modality from an individual stays together. Fit imputation, scaling, feature selection, target transformations, and learned preprocessing inside each training fold. Use only development validation results for hyperparameters and checkpoints. Unlock the final test once after the complete pipeline is frozen.

The present descriptive EDA includes the full tabular cohort and two inspection examples. A later holdout from these data cannot honestly be called completely unseen at the exploratory-analysis stage. Keep this exposure in the final report, freeze decisions before predictive experiments, and treat the resulting study as exploratory internal validation. A genuinely independent confirmation needs an untouched cohort or external replication. Do not hide this limitation by creating a split file retrospectively.

For regression, report MAE in seconds, RMSE, R², observed-versus-predicted plots, and uncertainty for the paired multimodal-versus-imaging error difference. Evaluate predictions on the original seconds scale even if a training-fitted log transformation is used. Accuracy, ROC-AUC, and an “80% accuracy” goal do not apply to this continuous target. Classification metrics belong only to a separately justified classification question.

## Leakage audit before training

| Risk | Required control | Current status |
|---|---|---|
| Participant or session overlap | Unique participant split; all sessions, slices, windows, modalities together | No split yet |
| Duplicate or near-duplicate images | Content hashes and image-similarity review within and across splits | Only the two-example downloads have provenance hashes; cohort image audit pending |
| Data-driven transforms | Fit within training fold; fixed external atlases documented separately | No predictive preprocessing fitted |
| Cognitive target proxies | Exclude TMT performance categories and related TMT fields from the primary feature set | Proposed; no model inputs built |
| Age encoded in biomarker | Exclude eGFR from primary age classification; cognition sensitivity analysis without eGFR | Identified |
| Acquisition round or sequence shortcuts | Compare age/sex/protocol composition; harmonize sequences or restrict cohort | Identified; full QC pending |
| Missingness selecting the cohort | Compare included/excluded demographics and report denominators | Initial availability matrix exists; final cohort analysis pending |
| Full-cohort EDA or target selection | Disclose current exposure; lock endpoint/features before modeling; external confirmation if needed | Exposure recorded |
| Augmentation or checkpoint choice using holdout | Training-only augmentation; development-only model selection; single final test evaluation | No training performed |

## Responsibilities and decision gates

Yekta should own unresolved ID/filename reconciliation, missingness and sampling audits, and cohort-wide imaging/signal QC. Melis and Elif should extend the evidence guide with claim-specific references for secondary markers, recording population, design, adjustment set, and causal limits. The technical lead should integrate those records, freeze the target and analysis plan with the team, then implement baseline comparisons and the simplest justified CNN.

Before implementation, resolve the conflicting blood-ID rows without guessing, determine the MRI/demographic mismatch and unusual EEG eye-condition filename, finalize eligible features and target, and agree on evaluation. No performance promise is justified by the current EDA.
