#!/usr/bin/env python
"""Participant master table: one row per LEMON participant from META, anthropometry, blood pressure, PSQ, TICS,
STAI and the availability tables, plus missingness and summary counts.

    uv run python analysis/participant_table/scripts/build_master_table.py

Reads data/LEMON (never modified). Writes master_table.csv and build_log.txt to data/derived/participant_table/
(git-ignored, participant-level) and the group-level missingness.csv and summary_counts.csv to
analysis/participant_table/results/. Short version of the local (unpublished) archive/original_code/participant_table/build.py; same outputs.
"""
import collections
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEMON = ROOT / "data/LEMON"
OUT = ROOT / "data/derived/participant_table"
RES = ROOT / "analysis/participant_table/results"
OUT.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
F = {"META": "META_File_IDs_Age_Gender_Education_Drug_Smoke_SKID_LEMON.csv",
     "ANTHRO": "Medical_LEMON/Anthropometry/Anthropometry_LEMON.csv",
     "BP": "Medical_LEMON/Blood Pressure/Blood_Pressure_LEMON.csv",
     "PSQ": "Emotion_and_Personality_Test_Battery_LEMON/PSQ.csv",
     "TICS": "Emotion_and_Personality_Test_Battery_LEMON/TICS.csv",
     "STAI": "Emotion_and_Personality_Test_Battery_LEMON/STAI_G_X2.csv",
     "D1": "Data_Availability_Tables/Availability_LEMON_Day1_Data.csv",
     "D2": "Data_Availability_Tables/Availability_LEMON_Day2_Data.csv",
     "FU": "Data_Availability_Tables/Availability_LEMON_Follo-up_Data.csv"}
DEC = re.compile(r"-?\d+,\d+")          # decimal comma, e.g. 3,5
log = []


def L(s):
    log.append(s); print(s)


def norm(s):
    return re.sub(r"^[Ss][Uu][Bb]-", "sub-", s.strip())


def text(key):
    return (LEMON / F[key]).read_bytes().decode("utf-8-sig", errors="replace")


def rd(key, delim=","):
    """{participant_id: {column: stripped value}}, header order kept; 'Sub-' normalised to 'sub-'."""
    rows = list(csv.reader(text(key).splitlines(), delimiter=delim))
    hdr = [h.strip() for h in rows[0]]
    return {norm(r[0]): {h: (r[i].strip() if i < len(r) else "") for i, h in enumerate(hdr) if h}
            for r in rows[1:] if r and r[0].strip()}, hdr


def num(s, cast):
    try:
        return cast(s)
    except (TypeError, ValueError):
        return ""


def mid(b):
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", b or "")
    return (int(m.group(1)) + int(m.group(2))) / 2 if m else ""


yn = lambda b: "yes" if b else "no"
S = {k: rd(k, ";" if k == "FU" else ",") for k in F}
TABLES = {k: v[0] for k, v in S.items()}
META, TICS_HDR = TABLES["META"], S["TICS"][1]

# ---- diagnostics: 'Sub-' prefixes and decimal commas
for key in ["ANTHRO", "BP"]:
    first = [ln.split(",")[0] for ln in text(key).splitlines()[1:]]
    cases = [c for c in first if c.lower() != c and c.startswith(("S", "s"))]
    L(f"ID case normalised in {key}: {len(cases)} IDs with 'Sub-' prefix e.g. {cases[:2]}")
ex = [(pid, c, v) for pid, rec in META.items() for c, v in rec.items() if DEC.fullmatch(v or "")]
for pid, c, v in ex:
    META[pid][c] = v.replace(",", ".")
L(f"Decimal-comma values converted in META: {len(ex)} (columns: {sorted({c for _, c, _ in ex})}) examples: {ex[:3]}")
other = sum(bool(DEC.fullmatch(v or "")) for k in ["ANTHRO", "BP", "PSQ", "TICS", "STAI", "D1", "D2", "FU"]
            for rec in TABLES[k].values() for v in rec.values())
L(f"Decimal-comma values found in other source files: {other}")

# ---- participants: everyone in META plus any core-file ID missing from META (BP-only IDs are excluded)
core = set().union(*(TABLES[k] for k in ["META", "ANTHRO", "PSQ", "TICS", "D1", "D2", "FU"]))
extra = sorted(core - set(META))
L(f"IDs in META: {len(META)}; extra IDs in core files not in META: {extra}")
L(f"BP file IDs: {len(TABLES['BP'])}; of which not in META: {len(set(TABLES['BP']) - set(META))} (excluded from master; see issues)")
universe = sorted(set(META) | set(extra))
L(f"Master rows: {len(universe)}")

# ---- output columns: (name, source table, source column); computed columns are filled below
SEX = "Gender_ 1=female_2=male"
SMOKE = "Smoking_num_(Non-smoker=1, Occasional Smoker=2, Smoker=3)"
COLS = ([("participant_id", None, None), ("in_META_file", None, None), ("age_bin_text", "META", "Age"),
         ("age_bin_midpoint_years", None, None), ("sex_coded_1female_2male", "META", SEX), ("sex_label", None, None),
         ("education", "META", "Education"), ("handedness", "META", "Handedness"),
         ("height_cm", "ANTHRO", "Height_cm"), ("weight_kg", "ANTHRO", "Weight_kg"), ("bmi_kg_per_m2", None, None)]
        + [(f"BP{n}_left_{s}", "BP", f"BP{n}_left_{s}") for n in (1, 2, 3) for s in ("systole", "diastole")]
        + [(c, "META", c) for c in ["Smoking", SMOKE, "AUDIT", "Standard_Alcoholunits_Last_28days", "DRUG",
                                    "DRUG_0=negative_1=Positive"]]
        + [("Unnamed: 7 (drug substance)", "META", "Unnamed: 7")]
        + [(c, "META", c) for c in ["Hamilton_Scale", "BSL23_sumscore", "BSL23_behavior"]]
        + [("STAI_Trait_Anxiety", "STAI", "STAI_Trait_Anxiety")]
        + [(c, "PSQ", c) for c in ["PSQ_Worries", "PSQ_Tension", "PSQ_Joy", "PSQ_Demands", "PSQ_OverallScore"]]
        + [(c, "TICS", c) for c in ["TICS_WorkOverload", "TICS_SocialOverload", "TICS_PressuereToPerform",
                                    "TICS_WorkDiscontent", "TICS_WorkDemands", "TICS_LackSocialRecognition",
                                    "TICS_SocialTension", "TICS_SocialIsolation", "TICS_ChronicWorrying", "TICS_ScreeningScale"]]
        + [("has_PSQ", None, None), ("has_TICS", None, None)]
        + [(c, "META", c) for c in ["SKID_Diagnoses", "SKID_Diagnoses 1", "SKID_Diagnoses 2", "Comments_SKID_assessment",
                                    "Alcohol_Dependence_In_1st-3rd_Degree_relative", "Relationship_Status"]]
        + [("avail_day1_rs_fMRI", "D1", "rs-fMRI"), ("avail_day1_ECG", "D1", "ECG"),
           ("avail_day2_EEG_RestingState_Raw", "D2", "EEG_RestingState_Raw"), ("in_followup_file", None, None),
           ("has_cardiac", None, None), ("has_fmri_rest", None, None)])

rows = []
for pid in universe:
    r = {c: TABLES[t].get(pid, {}).get(sc, "") if t else "" for c, t, sc in COLS}
    a, t = TABLES["ANTHRO"].get(pid, {}), TABLES["TICS"].get(pid, {})
    h, w = num(a.get("Height_cm", ""), float), num(a.get("Weight_kg", ""), float)
    r.update(participant_id=pid, in_META_file=yn(pid in META), age_bin_midpoint_years=mid(r["age_bin_text"]),
             sex_label={"1": "female", "2": "male"}.get(r["sex_coded_1female_2male"], ""),
             bmi_kg_per_m2=round(w / ((h / 100) ** 2), 2) if h and w else "",
             has_PSQ=yn(TABLES["PSQ"].get(pid, {}).get("PSQ_OverallScore", "")),
             has_TICS=yn(any(t.get(c, "") for c in TICS_HDR if c.startswith("TICS_"))),
             in_followup_file=yn(pid in TABLES["FU"]))
    rows.append(r)

cols = [c for c, _, _ in COLS]
with open(OUT / "master_table.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.DictWriter(fh, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
L(f"Wrote master_table.csv: {len(rows)} rows x {len(cols)} columns")

# ---- missingness and summary counts (group-level)
n = len(rows)
miss = [(c, k, round(100 * k / n, 1), ">20%" if k / n > 0.2 else "")
        for c in cols for k in [sum(str(r[c]).strip() == "" for r in rows)]]
with open(RES / "missingness.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.writer(fh); wr.writerow(["column", "missing_n", "missing_pct", "over_20pct"]); wr.writerows(miss)
L("Columns >20% missing: " + ", ".join(c for c, _, _, f in miss if f))
age_c = collections.Counter(r["age_bin_text"] or "(missing)" for r in rows)
sex_c = collections.Counter(r["sex_label"] or "(missing)" for r in rows)
psq_n, tics_n = sum(r["has_PSQ"] == "yes" for r in rows), sum(r["has_TICS"] == "yes" for r in rows)
both = sum(r["has_PSQ"] == "yes" and r["has_TICS"] == "yes" for r in rows)
with open(RES / "summary_counts.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.writer(fh); wr.writerow(["group", "value", "count"]); wr.writerow(["total", "participants", n])
    wr.writerows([["age_bin", k, v] for k, v in sorted(age_c.items())] + [["sex", k, v] for k, v in sorted(sex_c.items())])
    wr.writerows([["has_PSQ", "yes", psq_n], ["has_TICS", "yes", tics_n], ["has_PSQ_and_TICS", "yes", both]])
L(f"Summary: total={n}, PSQ={psq_n}, TICS={tics_n}, both={both}")
L(f"Age bins: {dict(age_c)}"); L(f"Sex: {dict(sex_c)}")
bp_only = sorted(set(TABLES["BP"]) - set(META))
L(f"BP-only IDs (not in META, excluded from master): {len(bp_only)} -> {', '.join(bp_only)}")
(OUT / "build_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
