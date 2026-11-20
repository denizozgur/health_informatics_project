# LEMON paper and supplement review

Reviewed on 5 November 2026. These are methodological notes for the initial investigation, not a replication of either paper. Full texts were retrieved through the Europe PMC full-text XML service; supplementary archives were retrieved through its `supplementaryFiles` service. Originals and extracted text remain locally under `data/lemon/source/` and are excluded from Git.

## Babayan and colleagues 2019

[Original article and references](https://doi.org/10.1038/sdata.2018.308), [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6371893/).

The final described sample contains 227 participants: 153 younger and 74 older adults. One participant was excluded after acquisition because of brain pathology. That distinction helps explain why acquisition and repository descriptions can mention 228, but does not by itself resolve every discrepancy in the current archive.

The study is cross-sectional. MRI, blood, cognition, and anthropometry were collected on the first assessment day; resting EEG and most questionnaires on the second. EEG and fMRI therefore cannot be treated as synchronized recordings. Recruitment occurred in four rounds; the last round deliberately recruited young men. Acquisition round, sex, age group, and sequence availability can consequently be associated. The protocol also changed FLAIR and susceptibility sequences during acquisition.

The data descriptor documents acquisition, preprocessing, availability, and quality rather than demonstrating a predictive model. The released EEG pipeline includes downsampling, filtering, removal of problematic channels and intervals, PCA and ICA. A per-file header remains necessary because channels and retained duration vary. Imaging derivatives exist, but their transformations and QC must be reviewed before reuse.

The public demographic file reports five-year age bins. Bin midpoints are approximate covariates, not recovered exact ages. The described cohort has an age gap; it is unsuitable for claims about continuous lifespan trajectories across the unobserved middle-age range.

The Word supplement contains cross-subject fMRI/DWI coverage maps, age-group distributions of questionnaire scales, and a table of 109 participants shared with the companion Mendes protocol. The coverage maps demonstrate why a common image grid does not guarantee identical brain coverage. The questionnaire figures use Welch comparisons with a stringent multiplicity threshold. The additional ISA archive is retained locally as source metadata. It is not a participant master table for our analysis.

The usage notes prohibit identifying individuals from phenotype information. This project uses pseudonymous joins only, keeps source and participant-level outputs out of Git, and does not interpret free-text psychiatric records as disease-training labels.

## Lin and colleagues 2026

[Original article](https://doi.org/10.1038/s41398-026-04157-5), [PMC full text and supplement link](https://pmc.ncbi.nlm.nih.gov/articles/PMC13487156/).

The reported final analysis sample is 193, including 135 younger and 58 older adults. The paper combines DTI-ALPS, BOLD–CSF coupling, EEG power, serum measurements, and cognitive scores using association and moderation analyses. It does not establish out-of-sample prediction performance.

The DWI pipeline uses FSL corrections and tensor estimation. Forty-six small ROIs are placed in template space along the projection and association pathways; global and anterior/middle/posterior indices aggregate those measurements. The numerator/denominator expression as typeset should be checked against an implementation before replication: whether each pair is averaged matters to scale. Diffusion direction, gradient rotation, registration, ROI placement, and white-matter microstructure all matter. The index is an indirect proxy and is not a measured clearance rate.

The fMRI method uses separately processed gray-matter BOLD and bottom-slice CSF signals, with a manually reviewed CSF mask, then cross-correlations at different lags. The stated passband of 0.01–0.1 Hz is called “high-pass” in the text despite describing a bounded passband. Global-signal regression would change the quantity being measured; one cannot apply a generic connectivity pipeline uncritically.

The EEG method describes 250 Hz data, 1–45 Hz filtering, PCA/ICA, channel interpolation, average reference, restoration of FCz, and Welch estimation of relative 40 Hz power. The relative-power denominator, frequency integration window, Welch parameters, eye condition, and handling of discontinuities need an explicit implementation specification. Released EEG alone is not proof that every step of this paper has already been applied.

The statistical methods list age, sex, BMI, and recent alcohol consumption as covariates, plus FA and MD when analyzing ALPS. The discussion additionally mentions education, which is not the same adjustment set. The stated FDR families contain 72 correlation tests, 374 correlation tests, and 1,584 moderation tests. Group comparisons use ANCOVA. Cognitive-item availability can change denominators; at least some reported cognitive analyses use 192 rather than 193.

## Discrepancies that affect reproducibility

| Source detail | Why it needs clarification |
|---|---|
| 227 starting participants, 33 stated exclusions, 193 final participants | The subtraction leaves one participant unexplained. Do not reconstruct a subject list from these totals. |
| Nine listed age-bin counts sum to 199 before six sparse-bin exclusions | This supports 193 after that step but does not fully reconcile the earlier exclusion arithmetic. |
| Results give negative 40 Hz–coupling coefficients approximately −0.18 to −0.14; discussion calls them positive and gives another inconsistent range | Preserve the signed coupling definition. A less negative coupling value and a weaker absolute coupling magnitude are different descriptions. |
| Main Figure 3 caption equates two TRs to four seconds; supplement gives TR 1.4 seconds | Lag in seconds must be calculated from the actual sequence timing and any documented resampling. |
| Supplement states 4,657 fMRI time points, TR 1.4 s, and a 15 min 30 s scan | Those values cannot all describe the same time series. Check image headers rather than copying them. |
| Statistical methods and discussion list different covariates | Specify our own adjustment set in advance; do not claim an exact reproduction. |

The 2026 Word supplement adds participant exclusions, acquisition parameters, third-TR coupling comparisons, additional moderation plots, and age/gamma plots. Its plots support inspection of the published analyses, not an independent validation dataset. The supplement’s alpha transparency requires a white background when inspecting its first TIFF figure.

## Consequences for this project

Use current participant-level files to establish cohort membership. Treat published associations as motivation, not target features or expected performance. No published glymphatic metric or gamma coefficient has been copied into our master table. Our initial statistics concern measured tabular data only; MRI/EEG examples are for inspection. Any replication requires a separate, explicit method and provenance record.
