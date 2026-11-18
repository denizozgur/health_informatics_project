import csv, re, os, collections
BASE = "/mnt/user-data/uploads/health_informatics_project/data/LEMON/"
OUT = "/mnt/user-data/outputs/task4/"
REL = "data/LEMON/"
F = {
 "META": "META_File_IDs_Age_Gender_Education_Drug_Smoke_SKID_LEMON.csv",
 "ANTHRO": "Medical_LEMON/Anthropometry/Anthropometry_LEMON.csv",
 "BP": "Medical_LEMON/Blood Pressure/Blood_Pressure_LEMON.csv",
 "PSQ": "Emotion_and_Personality_Test_Battery_LEMON/PSQ.csv",
 "TICS": "Emotion_and_Personality_Test_Battery_LEMON/TICS.csv",
 "STAI": "Emotion_and_Personality_Test_Battery_LEMON/STAI_G_X2.csv",
 "D1": "Data_Availability_Tables/Availability_LEMON_Day1_Data.csv",
 "D2": "Data_Availability_Tables/Availability_LEMON_Day2_Data.csv",
 "FU": "Data_Availability_Tables/Availability_LEMON_Follo-up_Data.csv",
}
log = []
def L(s): log.append(s); print(s)
def rd(key, delim=','):
    txt = open(BASE+F[key],'rb').read().decode('utf-8-sig', errors='replace')
    rows = list(csv.reader(txt.splitlines(), delimiter=delim))
    hdr = [h.strip() for h in rows[0]]
    recs = {}
    for r in rows[1:]:
        if not r or not r[0].strip(): continue
        pid = norm(r[0])
        recs[pid] = {hdr[i]: (r[i].strip() if i < len(r) else '') for i in range(len(hdr)) if hdr[i]}
    return recs, hdr
def norm(s):
    s = s.strip()
    return re.sub(r'^[Ss][Uu][Bb]-', 'sub-', s)

META, mh = rd("META")
ANTH, _ = rd("ANTHRO")
BP, _ = rd("BP")
PSQ, _ = rd("PSQ")
TICS, th = rd("TICS")
STAI, _ = rd("STAI")
D1, _ = rd("D1")
D2, _ = rd("D2")
FU, _ = rd("FU", delim=';')

# ID normalisation diagnostics
raw_ids = {}
for key in ["ANTHRO","BP"]:
    txt = open(BASE+F[key],'rb').read().decode('utf-8-sig').splitlines()
    cases = [l.split(',')[0] for l in txt[1:] if l.split(',')[0].lower()!=l.split(',')[0] and l.split(',')[0].startswith(('S','s'))]
    L(f"ID case normalised in {key}: {len(cases)} IDs with 'Sub-' prefix e.g. {cases[:2]}")

# decimal comma conversion (only numeric columns; META Standard_Alcoholunits_Last_28days)
dc_count = 0; dc_examples = []
for pid, rec in META.items():
    for col, v in rec.items():
        if re.fullmatch(r'-?\d+,\d+', v or ''):
            dc_examples.append((pid, col, v))
            rec[col] = v.replace(',', '.'); dc_count += 1
L(f"Decimal-comma values converted in META: {dc_count} (columns: {sorted({c for _,c,_ in dc_examples})}) examples: {dc_examples[:3]}")
# Check decimal commas elsewhere
other = 0
for name, src in [("ANTH",ANTH),("BP",BP),("PSQ",PSQ),("TICS",TICS),("STAI",STAI),("D1",D1),("D2",D2),("FU",FU)]:
    for pid, rec in src.items():
        for col, v in rec.items():
            if re.fullmatch(r'-?\d+,\d+', v or ''): other += 1
L(f"Decimal-comma values found in other source files: {other}")

AGE_BINS = {}
def mid(b):
    m = re.fullmatch(r'\s*(\d+)\s*-\s*(\d+)\s*', b or '')
    return (int(m.group(1))+int(m.group(2)))/2 if m else ''

# universe: META rows + any core-file ID not in META
core_ids = set(META) | set(ANTH) | set(PSQ) | set(TICS) | set(D1) | set(D2) | set(FU)
extra = sorted(core_ids - set(META))
bp_extra = sorted(set(BP) - set(META))
L(f"IDs in META: {len(META)}; extra IDs in core files not in META: {extra}")
L(f"BP file IDs: {len(BP)}; of which not in META: {len(bp_extra)} (excluded from master; see issues)")
universe = sorted(set(META)|set(extra))
L(f"Master rows: {len(universe)}")

def yn(b): return 'yes' if b else 'no'
def toint(s):
    try: return int(float(s))
    except: return ''
def tofloat(s):
    try: return float(s)
    except: return ''

rows_out = []
for pid in universe:
    m = META.get(pid, {})
    a = ANTH.get(pid, {}); b = BP.get(pid, {}); p = PSQ.get(pid, {}); t = TICS.get(pid, {})
    s = STAI.get(pid, {}); d1 = D1.get(pid, {}); d2 = D2.get(pid, {})
    age = m.get('Age','')
    sex = m.get('Gender_ 1=female_2=male','')
    h_cm = tofloat(a.get('Height_cm','')); w_kg = tofloat(a.get('Weight_kg',''))
    bmi = round(w_kg/((h_cm/100)**2), 2) if h_cm and w_kg else ''
    psq_has = yn(p.get('PSQ_OverallScore',''))
    tics_vals = [t.get(c,'') for c in th if c.startswith('TICS_')]
    tics_has = yn(any(v for v in tics_vals))
    fu_has = yn(pid in FU)
    row = {
     'participant_id': pid,
     'in_META_file': yn(pid in META),
     'age_bin_text': age,
     'age_bin_midpoint_years': mid(age),
     'sex_coded_1female_2male': sex,
     'sex_label': {'1':'female','2':'male'}.get(sex,''),
     'education': m.get('Education',''),
     'handedness': m.get('Handedness',''),
     'height_cm': a.get('Height_cm',''),
     'weight_kg': a.get('Weight_kg',''),
     'bmi_kg_per_m2': bmi,
     'BP1_left_systole': b.get('BP1_left_systole',''),
     'BP1_left_diastole': b.get('BP1_left_diastole',''),
     'BP2_left_systole': b.get('BP2_left_systole',''),
     'BP2_left_diastole': b.get('BP2_left_diastole',''),
     'BP3_left_systole': b.get('BP3_left_systole',''),
     'BP3_left_diastole': b.get('BP3_left_diastole',''),
     'Smoking': m.get('Smoking',''),
     'Smoking_num_(Non-smoker=1, Occasional Smoker=2, Smoker=3)': m.get('Smoking_num_(Non-smoker=1, Occasional Smoker=2, Smoker=3)',''),
     'AUDIT': m.get('AUDIT',''),
     'Standard_Alcoholunits_Last_28days': m.get('Standard_Alcoholunits_Last_28days',''),
     'DRUG': m.get('DRUG',''),
     'DRUG_0=negative_1=Positive': m.get('DRUG_0=negative_1=Positive',''),
     'Unnamed: 7 (drug substance)': m.get('Unnamed: 7',''),
     'Hamilton_Scale': m.get('Hamilton_Scale',''),
     'BSL23_sumscore': m.get('BSL23_sumscore',''),
     'BSL23_behavior': m.get('BSL23_behavior',''),
     'STAI_Trait_Anxiety': s.get('STAI_Trait_Anxiety',''),
     'PSQ_Worries': p.get('PSQ_Worries',''),
     'PSQ_Tension': p.get('PSQ_Tension',''),
     'PSQ_Joy': p.get('PSQ_Joy',''),
     'PSQ_Demands': p.get('PSQ_Demands',''),
     'PSQ_OverallScore': p.get('PSQ_OverallScore',''),
     'TICS_WorkOverload': t.get('TICS_WorkOverload',''),
     'TICS_SocialOverload': t.get('TICS_SocialOverload',''),
     'TICS_PressuereToPerform': t.get('TICS_PressuereToPerform',''),
     'TICS_WorkDiscontent': t.get('TICS_WorkDiscontent',''),
     'TICS_WorkDemands': t.get('TICS_WorkDemands',''),
     'TICS_LackSocialRecognition': t.get('TICS_LackSocialRecognition',''),
     'TICS_SocialTension': t.get('TICS_SocialTension',''),
     'TICS_SocialIsolation': t.get('TICS_SocialIsolation',''),
     'TICS_ChronicWorrying': t.get('TICS_ChronicWorrying',''),
     'TICS_ScreeningScale': t.get('TICS_ScreeningScale',''),
     'has_PSQ': psq_has,
     'has_TICS': tics_has,
     'SKID_Diagnoses': m.get('SKID_Diagnoses',''),
     'SKID_Diagnoses 1': m.get('SKID_Diagnoses 1',''),
     'SKID_Diagnoses 2': m.get('SKID_Diagnoses 2',''),
     'Comments_SKID_assessment': m.get('Comments_SKID_assessment',''),
     'Alcohol_Dependence_In_1st-3rd_Degree_relative': m.get('Alcohol_Dependence_In_1st-3rd_Degree_relative',''),
     'Relationship_Status': m.get('Relationship_Status',''),
     'avail_day1_rs_fMRI': d1.get('rs-fMRI',''),
     'avail_day1_ECG': d1.get('ECG',''),
     'avail_day2_EEG_RestingState_Raw': d2.get('EEG_RestingState_Raw',''),
     'in_followup_file': fu_has,
     'has_cardiac': '',
     'has_fmri_rest': '',
    }
    rows_out.append(row)

# convert decimal commas inside alcohol column already done; ensure numeric text kept
cols = list(rows_out[0].keys())
with open(OUT+'master_table.csv','w',newline='',encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for r in rows_out: w.writerow(r)
L(f"Wrote master_table.csv: {len(rows_out)} rows x {len(cols)} columns")

# missingness
miss = []
n = len(rows_out)
for c in cols:
    k = sum(1 for r in rows_out if str(r[c]).strip()=='')
    miss.append((c, k, round(100*k/n,1), '>20%' if k/n>0.2 else ''))
with open(OUT+'missingness.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh); w.writerow(['column','missing_n','missing_pct','over_20pct']); w.writerows(miss)
L("Columns >20% missing: " + ", ".join(c for c,k,p,f in miss if f))

# summary counts
age_c = collections.Counter(r['age_bin_text'] or '(missing)' for r in rows_out)
sex_c = collections.Counter(r['sex_label'] or '(missing)' for r in rows_out)
psq_n = sum(1 for r in rows_out if r['has_PSQ']=='yes')
tics_n = sum(1 for r in rows_out if r['has_TICS']=='yes')
both = sum(1 for r in rows_out if r['has_PSQ']=='yes' and r['has_TICS']=='yes')
with open(OUT+'summary_counts.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh); w.writerow(['group','value','count'])
    w.writerow(['total','participants',n])
    for k,v in sorted(age_c.items()): w.writerow(['age_bin',k,v])
    for k,v in sorted(sex_c.items()): w.writerow(['sex',k,v])
    w.writerow(['has_PSQ','yes',psq_n]); w.writerow(['has_TICS','yes',tics_n]); w.writerow(['has_PSQ_and_TICS','yes',both])
L(f"Summary: total={n}, PSQ={psq_n}, TICS={tics_n}, both={both}")
L(f"Age bins: {dict(age_c)}"); L(f"Sex: {dict(sex_c)}")
with open(OUT+'build_log.txt','w',encoding='utf-8') as fh: fh.write("\n".join(log)+"\n")
