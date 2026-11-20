#!/usr/bin/env python
"""Availability flags (ECG, rs-fMRI, physiology), overlap counts with PSQ/TICS, and the slim analysis table.

    uv run python analysis/participant_table/scripts/availability_flags.py      # after build_master_table.py

Flags come from the availability tables only (1 = listed as available), not from checking the data files.
Writes master_table_with_flags.csv and analysis_slim.csv to data/derived/participant_table/ (git-ignored) and the
group-level availability_counts.csv, ecg_frmi_psq_by_age_sex.csv and psq_by_age_group.csv to
analysis/participant_table/results/. Short version of the local (unpublished) archive/original_code/participant_table/
{flags_and_slim.py, counts_slim.py}; same outputs.
"""
import csv
import re
import statistics as st
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
AV = ROOT / "data/LEMON/Data_Availability_Tables"
OUT = ROOT / "data/derived/participant_table"
RES = ROOT / "analysis/participant_table/results"


def table(name, delim=","):
    rows = list(csv.reader((AV / name).read_bytes().decode("utf-8-sig", errors="replace").splitlines(), delimiter=delim))
    hdr = [h.strip() for h in rows[0]]
    return {re.sub(r"^[Ss][Uu][Bb]-", "sub-", r[0].strip()): dict(zip(hdr, r)) for r in rows[1:] if r and r[0].strip()}, hdr


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(header); w.writerows(rows)


flag = lambda v: {"1": 1, "0": 0}.get((v or "").strip())


def any_flag(rec, cols):
    vals = [flag(rec.get(c, "")) for c in cols]
    return "" if all(v is None for v in vals) else int(any(v == 1 for v in vals))


D1, _ = table("Availability_LEMON_Day1_Data.csv")
FU, hf = table("Availability_LEMON_Follo-up_Data.csv", ";")
FU_GROUPS = {"fu_ecg_any": [c for c in hf if c.endswith("_ecg")], "fu_bpp_any": [c for c in hf if c.endswith("_bpp")],
             "fu_ppg_any": [c for c in hf if c.endswith("_ppg")], "fu_resp_any": [c for c in hf if c.endswith("_resp")],
             "fu_any_ses2_physio": [c for c in hf if c.startswith("ses2_")]}
D1_FLAGS = {"has_cardiac_flag": "ECG", "has_fmri_rest_flag": "rs-fMRI",
            "d1_blood_pressure_beat_to_beat_flag": "Blood_pressure_beat-to-beat",
            "d1_pulse_photoplethysmography_flag": "Pulse_Photoplethysmography", "d1_respiration_flag": "Respiration"}

# ---- flags added to the master table
rows = []
for m in csv.DictReader(open(OUT / "master_table.csv", encoding="utf-8")):
    r, d1, fu = dict(m), D1.get(m["participant_id"], {}), FU.get(m["participant_id"])
    r.update({k: flag(d1.get(c, "")) for k, c in D1_FLAGS.items()})
    r.update({k: ("" if fu is None else any_flag(fu, cols)) for k, cols in FU_GROUPS.items()})
    rows.append(r)
with open(OUT / "master_table_with_flags.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
rows = list(csv.DictReader(open(OUT / "master_table_with_flags.csv", encoding="utf-8")))   # same as the original: re-read as text

# ---- overlap counts
yes = lambda r, c: r[c] == "yes"
ecg = [r for r in rows if r["has_cardiac_flag"] == "1"]
fmri = [r for r in rows if r["has_fmri_rest_flag"] == "1"]
both = [r for r in ecg if r["has_fmri_rest_flag"] == "1"]
write(RES / "availability_counts.csv", ["group", "n", "with_PSQ", "with_TICS", "with_PSQ_and_TICS"],
      [[lbl, len(g), sum(yes(r, "has_PSQ") for r in g), sum(yes(r, "has_TICS") for r in g),
        sum(yes(r, "has_PSQ") and yes(r, "has_TICS") for r in g)]
       for lbl, g in [("all", rows), ("ECG_flag", ecg), ("rsfMRI_flag", fmri), ("ECG_and_rsfMRI", both)]])
trip = [r for r in both if yes(r, "has_PSQ")]
bins = sorted({r["age_bin_text"] for r in rows if r["age_bin_text"]}, key=lambda b: int(b.split("-")[0]))
tab = [(b, s, n) for b in bins + ["(missing)"] for s in ["female", "male", "(missing)"]
       for n in [sum((r["age_bin_text"] or "(missing)") == b and (r["sex_label"] or "(missing)") == s for r in trip)] if n]
write(RES / "ecg_frmi_psq_by_age_sex.csv", ["age_bin", "sex", "n_ECG_and_rsfMRI_and_PSQ"], tab)


def psq_in(lo, hi):
    return [float(r["PSQ_OverallScore"]) for r in rows if r["age_bin_text"] and r["PSQ_OverallScore"] != ""
            and int(r["age_bin_text"].split("-")[0]) >= lo and int(r["age_bin_text"].split("-")[1]) <= hi]


write(RES / "psq_by_age_group.csv", ["age_group", "n", "mean_PSQ_OverallScore", "sd_PSQ_OverallScore"],
      [[f"{lo}-{hi}", len(g), round(st.mean(g), 2), round(st.stdev(g), 2)] for lo, hi in [(20, 40), (55, 80)] for g in [psq_in(lo, hi)]])

# ---- slim analysis table: no free text, diagnoses or drug results; META participants only
KEEP = (["participant_id", "age_bin_text", "age_bin_midpoint_years", "sex_coded_1female_2male", "sex_label", "bmi_kg_per_m2"]
        + [f"BP{n}_left_{s}" for n in (1, 2, 3) for s in ("systole", "diastole")]
        + ["Smoking_num_(Non-smoker=1, Occasional Smoker=2, Smoker=3)", "AUDIT", "Hamilton_Scale", "BSL23_sumscore", "STAI_Trait_Anxiety",
           "PSQ_Worries", "PSQ_Tension", "PSQ_Joy", "PSQ_Demands", "PSQ_OverallScore",
           "TICS_WorkOverload", "TICS_SocialOverload", "TICS_PressuereToPerform", "TICS_WorkDiscontent", "TICS_WorkDemands",
           "TICS_LackSocialRecognition", "TICS_SocialTension", "TICS_SocialIsolation", "TICS_ChronicWorrying", "TICS_ScreeningScale",
           "has_PSQ", "has_TICS", "has_cardiac_flag", "has_fmri_rest_flag"] + list(FU_GROUPS) + ["in_followup_file"])
with open(OUT / "analysis_slim.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=KEEP); w.writeheader()
    w.writerows({k: r[k] for k in KEEP} for r in rows if r["in_META_file"] == "yes")
print(f"flags: {len(rows)} rows; ECG {len(ecg)}, rs-fMRI {len(fmri)}, both {len(both)}, both + PSQ {len(trip)}; "
      f"slim table {sum(r['in_META_file'] == 'yes' for r in rows)} rows x {len(KEEP)} columns")

# ---- richer group-level summaries (no participant rows): flag counts, descriptives, categorical counts
T = pd.read_csv(OUT / "master_table_with_flags.csv", dtype=str)
FLAGS = list(D1_FLAGS) + list(FU_GROUPS)
pd.DataFrame([{"flag": f, "source": D1_FLAGS.get(f, "follow-up table, any of: " + ", ".join(FU_GROUPS.get(f, []))),
               "available_1": int((T[f] == "1").sum()), "not_available_0": int((T[f] == "0").sum()),
               "not_in_table_blank": int(T[f].isna().sum())} for f in FLAGS]).to_csv(RES / "availability_flag_counts.csv", index=False)
NUM = ["age_bin_midpoint_years", "height_cm", "weight_kg", "bmi_kg_per_m2"] + [f"BP{n}_left_{s}" for n in (1, 2, 3) for s in ("systole", "diastole")] \
    + ["AUDIT", "Standard_Alcoholunits_Last_28days", "Hamilton_Scale", "BSL23_sumscore", "STAI_Trait_Anxiety"] \
    + [c for c in T if c.startswith(("PSQ_", "TICS_"))]
X = T[NUM].apply(pd.to_numeric, errors="coerce")
grp = pd.Series(pd.to_numeric(T["age_bin_midpoint_years"], errors="coerce").ge(55).map({True: "older (55-80)", False: "younger (20-40)"}))
grp[T["age_bin_midpoint_years"].isna()] = "age missing"
desc = []
for g, idx in [("all", X.index)] + [(k, grp.index[grp == k]) for k in ["younger (20-40)", "older (55-80)"]]:
    d = X.loc[idx].describe().T
    d.insert(0, "group", g); d.insert(1, "missing", X.loc[idx].isna().sum())
    desc.append(d.rename(columns={"count": "n", "50%": "median", "25%": "q25", "75%": "q75"}))
pd.concat(desc).rename_axis("variable").reset_index().round(2).astype({"n": int}).to_csv(RES / "descriptives.csv", index=False)
cat = [(v, k, n) for v in ["sex_label", "age_bin_text", "handedness", "Smoking"]
       for k, n in T[v].fillna("(missing)").value_counts().sort_index().items()]
pd.DataFrame(cat, columns=["variable", "value", "n"]).to_csv(RES / "categorical_counts.csv", index=False)
print("also wrote results/availability_flag_counts.csv, descriptives.csv, categorical_counts.csv")
