#!/usr/bin/env python
"""Data dictionary for the participant master table: one row per column (type, source, meaning, notes).

    uv run python analysis/participant_table/scripts/data_dictionary.py      # after build_master_table.py

Writes analysis/participant_table/results/data_dictionary.csv and checks that every master-table column is documented.
Same content as the local (unpublished) archive/original_code/participant_table/dict.py (participant IDs removed from the notes); paths fixed.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "analysis/participant_table/results"
MASTER = ROOT / "data/derived/participant_table/master_table.csv"
META="data/LEMON/META_File_IDs_Age_Gender_Education_Drug_Smoke_SKID_LEMON.csv"
ANTH="data/LEMON/Medical_LEMON/Anthropometry/Anthropometry_LEMON.csv"
BP="data/LEMON/Medical_LEMON/Blood Pressure/Blood_Pressure_LEMON.csv"
PSQ="data/LEMON/Emotion_and_Personality_Test_Battery_LEMON/PSQ.csv"
TICS="data/LEMON/Emotion_and_Personality_Test_Battery_LEMON/TICS.csv"
STAI="data/LEMON/Emotion_and_Personality_Test_Battery_LEMON/STAI_G_X2.csv"
D1="data/LEMON/Data_Availability_Tables/Availability_LEMON_Day1_Data.csv"
D2="data/LEMON/Data_Availability_Tables/Availability_LEMON_Day2_Data.csv"
FU="data/LEMON/Data_Availability_Tables/Availability_LEMON_Follo-up_Data.csv"
M=META
rows=[
("participant_id","derived","-","Participant ID in BIDS form (prefix sub- plus six digits). 'Sub-' capitalisation in source normalised to 'sub-'.", "all ID-based files","Universe = 227 META IDs + the follow-up-only ID (only in follow-up file)"),
("in_META_file","derived","-","yes if ID appears in the META file; no otherwise",M,"the follow-up-only ID = no"),
("age_bin_text","raw",M+" :: Age","Age as 5-year bin text, e.g. 20-25. Not an exact age.",M,""),
("age_bin_midpoint_years","derived","computed from age_bin_text","MIDPOINT of the bin (lower+upper)/2, e.g. 20-25 -> 22.5. NOT an exact age.",M,"blank when no bin"),
("sex_coded_1female_2male","raw",M+" :: Gender_ 1=female_2=male","Sex code as in file: 1 = female, 2 = male",M,"Matches INFO file coding (1=female; 2=male) - no difference"),
("sex_label","derived","from sex code","female/male label from the code above",M,""),
("education","raw",M+" :: Education","School level (free text as in file)",M,"Contains a stray meeting note and typos (see issues)"),
("handedness","raw",M+" :: Handedness","right / left / ambidextrous (as in file)",M,"'ambedextor ' typo kept as in file"),
("height_cm","raw",ANTH+" :: Height_cm","Body height in cm (Day 1)",ANTH,""),
("weight_kg","raw",ANTH+" :: Weight_kg","Body weight in kg (Day 1)",ANTH,""),
("bmi_kg_per_m2","derived","Weight_kg / (Height_cm/100)^2 from "+ANTH,"Body mass index = weight(kg) / height(m)^2, rounded to 2 dp",ANTH,"blank if height or weight missing"),
("BP1_left_systole","raw",BP+" :: BP1_left_systole","Systolic BP, left arm, before MRI (Day 1)",BP,"Source info: BP1 before MRI"),
("BP1_left_diastole","raw",BP+" :: BP1_left_diastole","Diastolic BP, left arm, before MRI (Day 1)",BP,""),
("BP2_left_systole","raw",BP+" :: BP2_left_systole","Systolic BP, left arm, after MRI (Day 1)",BP,""),
("BP2_left_diastole","raw",BP+" :: BP2_left_diastole","Diastolic BP, left arm, after MRI (Day 1)",BP,""),
("BP3_left_systole","raw",BP+" :: BP3_left_systole","Systolic BP, left arm, at follow-up",BP,"Follow-up only"),
("BP3_left_diastole","raw",BP+" :: BP3_left_diastole","Diastolic BP, left arm, at follow-up",BP,"Follow-up only"),
("Smoking","raw",M+" :: Smoking","Smoking status text: non-smoker / occasional smoker / smoker / smoker?",M,"'smoker?' for one participant is UNCLEAR (uncertain entry)"),
("Smoking_num_(Non-smoker=1, Occasional Smoker=2, Smoker=3)","raw",M+" :: Smoking_num_(...)","Numeric smoking code: 1 non-smoker, 2 occasional smoker, 3 smoker (coding matches file header)",M,""),
("AUDIT","raw",M+" :: AUDIT","Alcohol Use Disorder Identification Test score (Day 2)",M,""),
("Standard_Alcoholunits_Last_28days","raw (decimal commas converted)",M+" :: Standard_Alcoholunits_Last_28days","Standard alcohol units in last 28 days",M,"32 values converted from decimal comma (e.g. '36,5' -> 36.5)"),
("DRUG","raw",M+" :: DRUG","Day 2 drug strip test result (text): negative / positive (substance)",M,"Trailing spaces stripped; spelling 'possitive' in source kept as-is? see issues"),
("DRUG_0=negative_1=Positive","raw",M+" :: DRUG_0=negative_1=Positive","Drug screen result coded 0 = negative, 1 = positive",M,""),
("Unnamed: 7 (drug substance)","raw",M+" :: Unnamed: 7","Drug substance flagged in the unnamed column 8 of META (BZO, THC, MOP)",M,"Column header is 'Unnamed: 7' in source"),
("Hamilton_Scale","raw",M+" :: Hamilton_Scale","Hamilton Depression Scale score (depression-related)",M,""),
("BSL23_sumscore","raw",M+" :: BSL23_sumscore","Borderline Symptomatology (BSL-23) sum score",M,""),
("BSL23_behavior","raw",M+" :: BSL23_behavior","BSL-23 behaviour subscale (as in file)",M,""),
("STAI_Trait_Anxiety","raw",STAI+" :: STAI_Trait_Anxiety","State-Trait Anxiety Inventory, trait anxiety (anxiety-related)",STAI,"220 rows in source"),
("PSQ_Worries","raw",PSQ+" :: PSQ_Worries","PSQ subscale Worries",PSQ,"Timeframe: last 2 years (PSQ_info)"),
("PSQ_Tension","raw",PSQ+" :: PSQ_Tension","PSQ subscale Tension",PSQ,""),
("PSQ_Joy","raw",PSQ+" :: PSQ_Joy","PSQ subscale Joy",PSQ,""),
("PSQ_Demands","raw",PSQ+" :: PSQ_Demands","PSQ subscale Demands",PSQ,""),
("PSQ_OverallScore","raw",PSQ+" :: PSQ_OverallScore","Perceived Stress Questionnaire overall score (exposure of interest)",PSQ,""),
("TICS_WorkOverload","raw",TICS+" :: TICS_WorkOverload","TICS subscale Work Overload",TICS,"Timeframe: last 3 months (TICS_info)"),
("TICS_SocialOverload","raw",TICS+" :: TICS_SocialOverload","TICS subscale Social Overload",TICS,""),
("TICS_PressuereToPerform","raw",TICS+" :: TICS_PressuereToPerform","TICS subscale Pressure To Perform (source spelling kept)",TICS,""),
("TICS_WorkDiscontent","raw",TICS+" :: TICS_WorkDiscontent","TICS subscale Work Discontent",TICS,""),
("TICS_WorkDemands","raw",TICS+" :: TICS_WorkDemands","TICS subscale Excessive Demands at Work",TICS,""),
("TICS_LackSocialRecognition","raw",TICS+" :: TICS_LackSocialRecognition","TICS subscale Lack Social Recognition",TICS,""),
("TICS_SocialTension","raw",TICS+" :: TICS_SocialTension","TICS subscale Social Tension",TICS,""),
("TICS_SocialIsolation","raw",TICS+" :: TICS_SocialIsolation","TICS subscale Social Isolation",TICS,""),
("TICS_ChronicWorrying","raw",TICS+" :: TICS_ChronicWorrying","TICS subscale Chronic Worrying",TICS,""),
("TICS_ScreeningScale","raw",TICS+" :: TICS_ScreeningScale","TICS screening scale",TICS,"No TICS total score column exists in source"),
("has_PSQ","derived","PSQ.csv :: PSQ_OverallScore non-empty","yes if the participant has a PSQ overall score",PSQ,""),
("has_TICS","derived","TICS.csv :: any TICS_* value non-empty","yes if the participant has at least one TICS value",TICS,""),
("SKID_Diagnoses","raw (free text)",M+" :: SKID_Diagnoses","SKID diagnosis result (free text, left as text)",M,""),
("SKID_Diagnoses 1","raw (free text)",M+" :: SKID_Diagnoses 1","SKID diagnosis 1 (free text)",M,""),
("SKID_Diagnoses 2","raw (free text)",M+" :: SKID_Diagnoses 2","SKID diagnosis 2 (free text)",M,"Mostly blank"),
("Comments_SKID_assessment","raw (free text)",M+" :: Comments_SKID_assessment","Free-text comment on SKID assessment",M,""),
("Alcohol_Dependence_In_1st-3rd_Degree_relative","raw",M+" :: Alcohol_Dependence_In_1st-3rd_Degree_relative","Family history of alcohol dependence (text: Yes/No/unknown/with degree numbers)",M,"Mixed text values kept as-is"),
("Relationship_Status","raw",M+" :: Relationship_Status","In a relationship (text: Yes/No; lowercase variants also present)",M,"Case inconsistent in source (yes vs Yes); not normalised"),
("avail_day1_rs_fMRI","raw (availability flag)",D1+" :: rs-fMRI","1 = rs-fMRI data available on Day 1, 0 = not available",D1,"Availability table only, not the scan itself"),
("avail_day1_ECG","raw (availability flag)",D1+" :: ECG","1 = ECG data available on Day 1, 0 = not",D1,"Availability table only"),
("avail_day2_EEG_RestingState_Raw","raw (availability flag)",D2+" :: EEG_RestingState_Raw","1 = resting-state EEG raw data available on Day 2, 0 = not",D2,"Availability table only"),
("in_followup_file","derived","Follow-up availability table :: ID present","yes if ID appears in the follow-up availability file",FU,"the follow-up-only ID appears only here"),
("has_cardiac","PLACEHOLDER","to be filled in STAGE B","Empty by design: cardiac data present (from heart-check lists)","-","Do not fill until heart check results are given"),
("has_fmri_rest","PLACEHOLDER","to be filled in STAGE B","Empty by design: resting fMRI present (from brain-check lists)","-","Do not fill until brain check results are given"),
]
with open(OUT / 'data_dictionary.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh); w.writerow(['column','type','source_file :: source_column','meaning','source_file','notes'])
    for r in rows: w.writerow([r[0],r[1],r[2],r[3],r[4],r[5]])
# check every master column is documented
hdr=next(csv.reader(open(MASTER,encoding='utf-8')))
documented={r[0] for r in rows}
print("undocumented columns:", [h for h in hdr if h not in documented])
print("dictionary rows:", len(rows), " master cols:", len(hdr))
