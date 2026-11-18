# Biological background for the LEMON project

This initial evidence guide connects variables actually present in the downloaded LEMON tables to candidate predictors. It separates physiological measurement from evidence about cognition. Established measurement validity does not imply established predictive usefulness in this small, selected cohort. No result below establishes a causal relationship within LEMON.

## Reading the biological measurements

Blood measurements describe the body outside the brain. MRI describes aspects of anatomy or an indirect physiological signal; EEG records voltage differences at the scalp. A cognitive score measures performance on a particular task. These are different measurement systems, collected at different times, rather than interchangeable measures of “brain health.”

An association can arise because one variable influences another, because both share causes such as age, or because recruitment and missingness select a particular subgroup. Multimodal prediction asks whether additional measurements improve predictions for held-out participants; that is distinct from explaining a biological mechanism.

## HbA1c

**Fields:** `HBA1C_in_%`, `HBA1CI_in_mmol_mol`; supporting hemoglobin measures include `HB_in_g_dl`, `HBA1G_in_g_dl`, and blood-count fields. The two HbA1c scales describe the same underlying quantity and should not both enter a small model without a reason.

HbA1c is the fraction of hemoglobin that has undergone glycation. Hemoglobin carries oxygen in red blood cells; glycation accumulates during their circulation. HbA1c therefore reflects glucose exposure over roughly the preceding two to three months, weighted by red-cell turnover. Anemia, altered cell lifespan, and assay effects can change the relationship to glucose. These are established measurement considerations, summarized in [Update on biomarkers of glycemic control](https://pmc.ncbi.nlm.nih.gov/articles/PMC6347654/).

Sustained dysglycemia may coexist with vascular and metabolic processes relevant to cognition. In the prospective ARIC cohort, midlife diabetes and elevated HbA1c categories were associated with greater later cognitive decline. This is longitudinal observational evidence, not proof that changing an individual LEMON participant’s HbA1c would improve cognition. [Rawlings et al. 2014](https://doi.org/10.7326/M14-0737).

**Evidence judgment:** established glycemia marker; moderately supported observational association with cognitive outcomes in broader populations; its incremental predictive value within healthy LEMON participants remains unknown. Consider glucose, BMI, age, renal measures, and blood counts when interpreting it. Do not select the memory endpoint because it happens to give the smallest EDA p-value.

## Glucose

**Field:** `GLU_in_mmol_l`. Glucose is a circulating energy substrate, including for the brain. A single blood draw is much more time-sensitive than HbA1c: recent meals, stress, and sampling conditions matter. The downloaded blood codebook documents timing relative to the assessment day but does not establish a standardized fasting state for every participant.

A prospective study relating repeated clinical glucose measurements to later dementia found an association even among participants without diabetes. That study concerned older adults and averaged measurements over time; it is not directly equivalent to one LEMON glucose value or a diagnosis label. [Crane et al. 2013](https://doi.org/10.1056/NEJMoa1215740).

**Evidence judgment:** established physiological measurement; observational support for long-term glycemic exposure and cognitive outcomes; a single-draw association in this cohort is uncertain. Expect partial overlap with HbA1c and metabolic measurements without assuming they are redundant.

## LDL HDL and total cholesterol

**Fields:** `LDLC_in_mmol_l`, `HDLC_in_mmol_l`, `CHOL_in_mmol_l`. Lipoproteins transport lipids in blood. LDL and HDL cholesterol quantify cholesterol carried in different particle classes; total cholesterol aggregates circulating fractions. They do not measure cholesterol inside the brain directly. Calling HDL simply “good” and LDL “bad” does not adequately describe a cognition analysis.

Potential relevance includes vascular disease pathways and shared metabolic exposures. Age at measurement matters: systematic evidence relating cholesterol to later dementia differs between midlife and late-life measurements. LDL, HDL, and total cholesterol should therefore be analyzed separately with their direction and population specified. [Anstey et al. 2017 review and meta-analysis](https://doi.org/10.3233/JAD-160826).

**Evidence judgment:** established lipid measurements; heterogeneous observational evidence for cognitive outcomes; a universal monotonic “higher LDL means worse cognition” rule is not justified. Correlations with triglycerides, BMI, age, and one another are plausible and should be measured rather than assumed. Use a limited feature set or regularization to handle overlap.

## Triglycerides

**Field:** `TRIG_in_mmol_l`. Triglycerides are an energy-storage lipid transported in lipoproteins. Their concentration depends on metabolic state and recent intake. Triglycerides, lipoprotein cholesterol, BMI, and glucose can be statistically related without measuring the same process.

Metabolic syndrome has been associated with poorer cognition and white-matter differences in observational research. Such evidence concerns a collection of exposures, rather than isolating triglycerides as a causal driver. [Dintica et al. 2022 CARDIA study](https://doi.org/10.3389/fnins.2022.942743).

**Evidence judgment:** established metabolic measurement; moderate support for broader metabolic-health associations, with individual-marker effects uncertain. Our observed right-skewed distribution motivates robust summaries and a possible training-only transformation later, not deletion of high values.

## Creatinine and CKD EPI eGFR

**Fields:** `CRE_in_µmol_l`, `CKDEPI_in_ml_min_1.73m`. Creatinine is related to muscle metabolism and renal filtration. eGFR estimates the rate at which kidneys filter blood, indexed to a standard body surface area. It is an equation output rather than a directly measured filtration rate.

CKD-EPI equations incorporate demographic information alongside serum markers; age and sex can therefore be encoded in the resulting predictor. The source column name alone does not establish which exact equation the laboratory used. Do not recompute exact eGFR from five-year age bins or assume the current equation was used for samples collected in 2013–2015. [Levey et al. 2009 equation study](https://doi.org/10.7326/0003-4819-150-9-200905050-00006).

Shared vascular exposures and renal physiology motivate a possible kidney–brain relationship, but the evidence is more nuanced than “low eGFR causes cognitive decline.” A prospective-study meta-analysis found mixed eGFR results and stronger evidence for albuminuria, which is a different measurement. Albuminuria has not been identified as an available predictor here. [Deckers et al. 2017](https://doi.org/10.1212/WNL.0000000000003482).

**Evidence judgment:** established estimation framework; mixed observational evidence for eGFR-specific cognitive outcomes; causal interpretation unsupported here. For age-group classification, exclude eGFR from the primary comparison because of its demographic construction. For cognition, compare against a demographic baseline and report a sensitivity analysis without eGFR. Its substantial missingness also reduces a seven-marker complete-case cohort.

## Blood pressure BMI and additional laboratory variables

**Fields:** `BP1_left_systole`, `BP1_left_diastole`, later BP measurements, pulse fields, `Height_cm`, `Weight_kg`, `Waist_cm`, and `Hip_cm`. BMI is derived as weight divided by height squared; it is a coarse size indicator, not a direct measure of body composition. BP records pressure during cardiac contraction and relaxation. Seated BP, pulse, and continuous MRI physiology are distinct measurements.

An observational Leipzig study associated higher BP with lower regional gray-matter volume in young adults. This supports a measured vascular covariate and a plausible research direction, without demonstrating BP-driven tissue loss in our sample. [Schaare et al. 2019](https://doi.org/10.1212/WNL.0000000000006947).

Additional available fields cover CRP, blood counts, electrolytes, liver enzymes, TSH, and coagulation. CRP is an inflammation-related blood marker; the current table includes left-censored CRP values and a long upper tail. Hemoglobin/hematocrit and cell counts describe blood composition; electrolytes relate to ionic balance; TSH relates to thyroid regulation; coagulation measures concern clotting. These are measurement descriptions from the LEMON codebook, **not completed claims about their cognitive associations**. Dedicated claim-specific literature review is still needed before promoting them to primary predictors. Reference ranges and hemolysis/lipemia indices should be treated as contextual or quality fields rather than automatic biological features.

## Brain imaging cognition and gamma oscillations

T1-weighted MRI provides tissue contrast useful for estimating regional anatomy after validated processing. T2 and FLAIR provide different contrast; these pilot FLAIR scans have thick slices, which limits comparisons in reconstructed planes. Pixel intensity is not a direct tissue volume or disease label. MRI-derived regional volumes or cortical measures would require a defined pipeline, anatomical QC, and intracranial-volume handling.

Broader population research links diabetes with cognitive and imaging differences, which motivates investigating systemic measurements alongside anatomy. Those clinical exposures and populations differ from LEMON, and observational cross-sectional “brain aging” patterns do not establish an individual rate of decline. [Antal et al. 2022](https://doi.org/10.7554/eLife.73138).

TMT-B measures timed number/letter alternation and combines executive demands with visual search and motor speed. CVLT learning total measures acquisition across repeated word-list trials; delayed recall measures retention and retrieval. WST concerns vocabulary rather than a global cognitive score. These interpretations and scoring directions follow the LEMON test codebooks and [dataset descriptor](https://doi.org/10.1038/sdata.2018.308). None is an Alzheimer’s diagnosis.

Gamma denotes relatively fast neural activity; 40 Hz means approximately forty oscillation cycles per second. Scalp power near 40 Hz can also include muscle activity, spectral background, and filtering effects. A single spectral ordinate is not proof of a neuronal gamma oscillation.

The glymphatic framework concerns exchange and transport involving cerebrospinal and interstitial fluid. Experimental tracer work supports a clearance-related pathway in animals; it does not make ALPS a direct clearance assay. [Iliff et al. 2012](https://doi.org/10.1126/scitranslmed.3003748). Human sleep research shows coupled neural, hemodynamic, and CSF dynamics, which is relevant to BOLD–CSF signals but differs from LEMON’s awake recordings. [Fultz et al. 2019](https://doi.org/10.1126/science.aax5440).

Gamma stimulation experiments provide mechanistic evidence in mouse models under specific interventions. Resting human gamma power is a different exposure. [Murdock et al. 2024](https://doi.org/10.1038/s41586-024-07132-6). The LEMON-based 2026 paper provides modest cross-sectional associations with indirect MRI proxies; causal protection or therapeutic efficacy cannot be inferred. [Lin et al. 2026](https://doi.org/10.1038/s41398-026-04157-5).

**Evidence judgment:** physiological motivation is credible; the specific resting-gamma → clearance → cognition chain in healthy humans remains a hypothesis. A full glymphatic replication is a substantially larger preprocessing and validation task than the initial multimodal prediction project.
