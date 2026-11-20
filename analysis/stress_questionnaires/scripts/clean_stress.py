#!/usr/bin/env python
"""Stress questionnaires (PSQ, TICS): raw-text checks, ID checks, descriptives, a clean table and score tests.

    uv run python analysis/stress_questionnaires/scripts/clean_stress.py

Reads data/LEMON (never modified). Writes participant-level files to data/derived/stress_questionnaires/
(git-ignored) and the histogram to analysis/stress_questionnaires/figures/.
Short version of the local (unpublished) archive/original_code/stress_questionnaires/{task2_stress.py, followup.py}; same outputs.
"""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
LEMON = ROOT / "data/LEMON"
EMO = LEMON / "Emotion_and_Personality_Test_Battery_LEMON"
OUT = ROOT / "data/derived/stress_questionnaires"
FIG = ROOT / "analysis/stress_questionnaires/figures"
RES = ROOT / "analysis/stress_questionnaires/results"
for d in (OUT, FIG, RES):
    d.mkdir(parents=True, exist_ok=True)
PSQ_SUBS = ["PSQ_Worries", "PSQ_Tension", "PSQ_Joy", "PSQ_Demands"]


def raw_check(path):
    """Count decimal-comma values and non-numeric cells in the raw text, before any parsing."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header, comma_dec, bad = lines[0].split(","), 0, []
    for ln in lines[1:]:
        cells = ln.split(",")
        for col, c in zip(header[1:], (x.strip() for x in cells[1:])):
            if re.fullmatch(r"\d+,\d+", c):
                comma_dec += 1
            elif c and not re.fullmatch(r"-?\d+(\.\d+)?", c):
                bad.append((cells[0], col, c))
    return {"lines_including_header": len(lines), "decimal_comma_values": comma_dec,
            "non_numeric_cells": bad[:20], "non_numeric_count": len(bad)}


def describe(s, allowed=None):
    v = pd.to_numeric(s, errors="coerce")
    d = {"n_nonmissing": int(v.notna().sum()), "n_missing": int(v.isna().sum())}
    if d["n_nonmissing"]:
        d.update({k: round(getattr(v, k)(), 3) for k in ["min", "max", "mean", "median"]})
        d.update(sd=round(v.std(), 3), skew=round(v.skew(), 3))
        sd = v.std()
        z = (v - v.mean()) / sd if sd and sd > 0 else v * np.nan
        d["n_beyond_3sd"] = int((z.abs() > 3).sum()); d["ids_beyond_3sd"] = list(v.index[z.abs() > 3])
    if allowed:
        out = v[(v < allowed[0]) | (v > allowed[1])]
        d["n_outside_range"] = int(len(out)); d["ids_outside_range"] = list(out.index)
    return d


def corr(a, b):
    p = pd.concat([a, b], axis=1).dropna()
    r, pv = stats.pearsonr(p.iloc[:, 0], p.iloc[:, 1]); rho, pr = stats.spearmanr(p.iloc[:, 0], p.iloc[:, 1])
    return {"n": int(len(p)), "pearson_r": round(r, 3), "pearson_p": float(f"{pv:.3g}"),
            "spearman_rho": round(rho, 3), "spearman_p": float(f"{pr:.3g}")}


# ---- raw checks, parsing, ID checks
files = {"PSQ": EMO / "PSQ.csv", "TICS": EMO / "TICS.csv"}
rep = {"raw_text_checks": {k: raw_check(p) for k, p in files.items()}}
raw = {k: pd.read_csv(p, dtype=str) for k, p in files.items()}
for name, df in raw.items():
    ids = df.iloc[:, 0]
    rep.update({f"{name}_shape": list(df.shape), f"{name}_id_column": df.columns[0],
                f"{name}_unique_ids": int(ids.nunique()), f"{name}_duplicate_ids": sorted(set(ids[ids.duplicated(keep=False)]))})
num = {k: df.apply(lambda c: c if c.name == "ID" else c.str.strip().str.replace(",", ".", regex=False)).set_index("ID")
       for k, df in raw.items()}
psq, tics = num["PSQ"], num["TICS"]
rep["decimal_commas_converted"] = {k: v["decimal_comma_values"] for k, v in rep["raw_text_checks"].items()}
meta = pd.read_csv(LEMON / "META_File_IDs_Age_Gender_Education_Drug_Smoke_SKID_LEMON.csv", dtype=str)
meta_ids = set(meta.iloc[:, 0].str.strip())
rep["meta_rows"] = int(len(meta))
for name, df in num.items():
    rep[f"{name}_ids_not_in_meta"] = sorted(set(df.index) - meta_ids)
for name, df in num.items():
    rep[f"meta_ids_missing_from_{name}"] = len(meta_ids - set(df.index))
rep["PSQ_ids_same_set_as_TICS"] = set(psq.index) == set(tics.index)

# ---- descriptives and outliers (PSQ scores are 0-100; TICS has no documented maximum)
rep["descriptives"] = {**{c: describe(psq[c], (0, 100)) for c in psq}, **{c: describe(tics[c]) for c in tics}}

# ---- does the PSQ overall score equal the mean of the four subscales? (tested, not assumed)
P = psq.apply(pd.to_numeric, errors="coerce")
both = pd.concat([P["PSQ_OverallScore"], P[PSQ_SUBS].mean(axis=1)], axis=1).dropna()
gap = (both.iloc[:, 0] - both.iloc[:, 1]).abs()
rep["PSQ_overall_vs_mean_of_subscales"] = {"n_compared": int(len(both)), "n_within_0.01": int((gap <= 0.01).sum()),
                                           "max_abs_difference": round(float(gap.max()), 3)}
# ---- does the TICS screening scale equal the sum of the nine subscales?
T = tics.apply(pd.to_numeric, errors="coerce")
subs = [c for c in T if c != "TICS_ScreeningScale"]
tsum, scr = T[subs].sum(axis=1, min_count=len(subs)), T["TICS_ScreeningScale"]
b2 = pd.concat([scr, tsum], axis=1).dropna()
rep["TICS_screening_vs_sum_of_subscales"] = {
    "n_compared": int(len(b2)), "n_equal": int(((b2.iloc[:, 0] - b2.iloc[:, 1]).abs() < 1e-9).sum()),
    "example_first_row_screening": float(b2.iloc[0, 0]) if len(b2) else None,
    "example_first_row_sum": float(b2.iloc[0, 1]) if len(b2) else None}

# ---- clean table: numbers only, no rows dropped, nothing imputed
clean = pd.concat([P, T], axis=1).reindex(sorted(set(psq.index) | set(tics.index)))
clean.index.name = "ID"
clean.reset_index().to_csv(OUT / "stress_clean.csv", index=False)
rep["clean_rows"] = int(len(clean)); rep["clean_columns"] = list(clean.columns)

# ---- histograms of the main score of each questionnaire
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for a, v, col, t in [(ax[0], P["PSQ_OverallScore"], "#4C72B0", "PSQ_OverallScore (values as stored in PSQ.csv)"),
                     (ax[1], scr, "#DD8452", "TICS_ScreeningScale (no total column found)")]:
    a.hist(v.dropna(), bins=20, color=col); a.set_title(t); a.set_xlabel("score"); a.set_ylabel("participants")
plt.tight_layout(); plt.savefig(FIG / "histograms_main_scores.png", dpi=120); plt.close()

# ---- PSQ overall vs TICS (no TICS total exists, so two stand-ins)
rep["correlations_PSQ_overall_vs_TICS"] = {"TICS_ScreeningScale": corr(P["PSQ_OverallScore"], scr),
                                           "sum_of_9_TICS_subscales (computed here)": corr(P["PSQ_OverallScore"], tsum)}
(OUT / "task2_checks.json").write_text(json.dumps(rep, indent=2, default=str))

# ---- follow-up: is the overall score the mean of the subscales with Joy reversed (100 - Joy)?
df = pd.read_csv(OUT / "stress_clean.csv")
res = {"input_file": str((OUT / "stress_clean.csv").relative_to(ROOT)), "rows": int(len(df))}
d = df.dropna(subset=["PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "PSQ_Joy", "PSQ_OverallScore"]).copy()
d["joy_reversed"] = 100 - d["PSQ_Joy"]
d["mean_4_reversed_joy"] = d[["PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "joy_reversed"]].mean(axis=1)
d["gap"] = (d["PSQ_OverallScore"] - d["mean_4_reversed_joy"]).abs()
res["test1"] = {"rows_with_all_five_values": int(len(d)), "n_within_0.01": int((d["gap"] <= 0.01).sum()),
                "largest_gap": round(float(d["gap"].max()), 4), "median_gap": round(float(d["gap"].median()), 4),
                "mean_signed_difference_overall_minus_mean": round(float((d["PSQ_OverallScore"] - d["mean_4_reversed_joy"]).mean()), 4),
                "pearson_r_overall_vs_mean": round(float(np.corrcoef(d["PSQ_OverallScore"], d["mean_4_reversed_joy"])[0, 1]), 4),
                "ids_with_largest_gap_top5": d.sort_values("gap", ascending=False)["ID"].head(5).tolist()}
d["mean_4_raw_joy"] = d[["PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "PSQ_Joy"]].mean(axis=1)
d["gap_raw"] = (d["PSQ_OverallScore"] - d["mean_4_raw_joy"]).abs()
res["test1_alt_joy_not_reversed"] = {"n_within_0.01": int((d["gap_raw"] <= 0.01).sum()), "largest_gap": round(float(d["gap_raw"].max()), 4),
                                     "pearson_r": round(float(np.corrcoef(d["PSQ_OverallScore"], d["mean_4_raw_joy"])[0, 1]), 4)}
# ---- correlation with and without the extreme TICS value found above
pair = df[["ID", "PSQ_OverallScore", "TICS_ScreeningScale"]].dropna()
OUTLIER = "sub-010134"
res["test2_all"] = corr(pair["PSQ_OverallScore"], pair["TICS_ScreeningScale"])
q = pair[pair["ID"] != OUTLIER]
res[f"test2_excluding_{OUTLIER}"] = corr(q["PSQ_OverallScore"], q["TICS_ScreeningScale"])
res[f"test2_{OUTLIER}_values"] = pair[pair["ID"] == OUTLIER].to_dict("records")
(OUT / "followup_checks.json").write_text(json.dumps(res, indent=2))
d[["ID", "PSQ_OverallScore", "PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "PSQ_Joy", "joy_reversed", "mean_4_reversed_joy",
   "gap", "mean_4_raw_joy", "gap_raw"]].to_csv(OUT / "followup_test1_rows.csv", index=False)
# ---- group-level summaries for Git (no participant rows or IDs)
meta_age = meta.set_index(meta.columns[0])["Age"].reindex(clean.index)
older = meta_age.str.split("-").str[0].astype(float).ge(55)
rows = []
for g, m in [("all", clean.index == clean.index), ("younger (20-40)", ~older & meta_age.notna()), ("older (55-80)", older)]:
    for c in clean:
        v = clean.loc[m, c]
        rows.append(dict(variable=c, group=g, n=int(v.notna().sum()), missing=int(v.isna().sum()), mean=v.mean(), sd=v.std(),
                         min=v.min(), median=v.median(), max=v.max(), skew=v.skew(),
                         n_beyond_3sd=int(((v - v.mean()).abs() > 3 * v.std()).sum())))
pd.DataFrame(rows).round(3).to_csv(RES / "score_descriptives.csv", index=False)
c_all, c_ex = res["test2_all"], res[f"test2_excluding_{OUTLIER}"]
pd.DataFrame([
    ("PSQ_OverallScore = mean of the 4 subscales", f"{rep['PSQ_overall_vs_mean_of_subscales']['n_within_0.01']} of {rep['PSQ_overall_vs_mean_of_subscales']['n_compared']} rows within 0.01", "no"),
    ("PSQ_OverallScore = mean of Worries, Tension, Demands and (100 - Joy)", f"{res['test1']['n_within_0.01']} of {res['test1']['rows_with_all_five_values']} rows within 0.01", "yes"),
    ("TICS_ScreeningScale = sum of the 9 subscales", f"{rep['TICS_screening_vs_sum_of_subscales']['n_equal']} of {rep['TICS_screening_vs_sum_of_subscales']['n_compared']} rows equal", "no"),
    ("PSQ_OverallScore vs TICS_ScreeningScale, all", f"Pearson r = {c_all['pearson_r']}, Spearman rho = {c_all['spearman_rho']}, n = {c_all['n']}", "strong positive"),
    ("PSQ_OverallScore vs TICS_ScreeningScale, without the most extreme TICS value", f"Pearson r = {c_ex['pearson_r']}, n = {c_ex['n']}", "almost unchanged"),
    ("IDs in PSQ/TICS not in META", f"{len(rep['PSQ_ids_not_in_meta'])} / {len(rep['TICS_ids_not_in_meta'])}", "all match"),
    ("Decimal commas in the raw files", f"PSQ {rep['decimal_commas_converted']['PSQ']}, TICS {rep['decimal_commas_converted']['TICS']}", "none"),
], columns=["check", "result", "conclusion"]).to_csv(RES / "score_checks.csv", index=False)
print(f"wrote {OUT.relative_to(ROOT)}/: stress_clean.csv ({len(clean)} rows), task2_checks.json, followup_checks.json, "
      f"followup_test1_rows.csv; {RES.relative_to(ROOT)}/score_descriptives.csv, score_checks.csv; figure histograms_main_scores.png")
