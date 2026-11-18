import json, os, re, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "/mnt/user-data/uploads/health_informatics_project/data/LEMON"
EMO = os.path.join(SRC, "Emotion_and_Personality_Test_Battery_LEMON")
META = os.path.join(SRC, "META_File_IDs_Age_Gender_Education_Drug_Smoke_SKID_LEMON.csv")
OUT = "/mnt/user-data/outputs/task2"
os.makedirs(OUT, exist_ok=True)
report = {}

def raw_check(path):
    """Count decimal-comma values and non-numeric cells in the raw text, before any parsing."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    header = lines[0].split(",")
    comma_dec = 0
    non_numeric = []
    for ln in lines[1:]:
        cells = ln.split(",")
        for col, cell in zip(header[1:], cells[1:]):
            c = cell.strip()
            if re.fullmatch(r"\d+,\d+", c):
                comma_dec += 1
            elif c != "" and not re.fullmatch(r"-?\d+(\.\d+)?", c):
                non_numeric.append((cells[0], col, c))
    return {"lines_including_header": len(lines), "decimal_comma_values": comma_dec,
            "non_numeric_cells": non_numeric[:20], "non_numeric_count": len(non_numeric)}

def describe(s, allowed=None):
    v = pd.to_numeric(s, errors="coerce")
    d = {"n_nonmissing": int(v.notna().sum()), "n_missing": int(v.isna().sum())}
    if d["n_nonmissing"]:
        d.update({"min": round(v.min(), 3), "max": round(v.max(), 3), "mean": round(v.mean(), 3),
                  "median": round(v.median(), 3), "sd": round(v.std(), 3),
                  "skew": round(v.skew(), 3)})
        sd = v.std()
        z = (v - v.mean()) / sd if sd and sd > 0 else v * np.nan
        d["n_beyond_3sd"] = int((z.abs() > 3).sum())
        d["ids_beyond_3sd"] = list(v.index[z.abs() > 3])
    if allowed:
        lo, hi = allowed
        out = v[(v < lo) | (v > hi)]
        d["n_outside_range"] = int(len(out))
        d["ids_outside_range"] = list(out.index)
    return d

# ---- Step 3 raw checks and parsing ----
files = {"PSQ": os.path.join(EMO, "PSQ.csv"), "TICS": os.path.join(EMO, "TICS.csv")}
raw = {k: raw_check(p) for k, p in files.items()}
report["raw_text_checks"] = raw

psq = pd.read_csv(files["PSQ"], dtype=str)
tics = pd.read_csv(files["TICS"], dtype=str)
for name, df in [("PSQ", psq), ("TICS", tics)]:
    report[f"{name}_shape"] = list(df.shape)
    report[f"{name}_id_column"] = df.columns[0]
    dup = df[df.iloc[:, 0].duplicated(keep=False)].iloc[:, 0].tolist()
    report[f"{name}_unique_ids"] = int(df.iloc[:, 0].nunique())
    report[f"{name}_duplicate_ids"] = sorted(set(dup))

# Decimal-comma conversion: only for values that match \d+,\d+ (none expected in the CSV text, verified above)
def to_num(df):
    out = df.copy()
    for c in out.columns[1:]:
        out[c] = out[c].str.strip().str.replace(",", ".", regex=False)
    return out

psq_n = to_num(psq).set_index("ID")
tics_n = to_num(tics).set_index("ID")
report["decimal_commas_converted"] = {k: raw[k]["decimal_comma_values"] for k in raw}

# ---- ID check against meta file ----
meta = pd.read_csv(META, dtype=str)
meta_ids = set(meta.iloc[:, 0].str.strip())
report["meta_rows"] = int(len(meta))
report["PSQ_ids_not_in_meta"] = sorted(set(psq_n.index) - meta_ids)
report["TICS_ids_not_in_meta"] = sorted(set(tics_n.index) - meta_ids)
report["meta_ids_missing_from_PSQ"] = len(meta_ids - set(psq_n.index))
report["meta_ids_missing_from_TICS"] = len(meta_ids - set(tics_n.index))
report["PSQ_ids_same_set_as_TICS"] = set(psq_n.index) == set(tics_n.index)

# ---- Step 4: descriptives and step 5: outliers ----
psq_ranges = {c: (0, 100) for c in psq_n.columns}           # PSQ values look like 0-100 scaled scores
tics_ranges = {c: (0, np.inf) for c in tics_n.columns}     # no documented max for TICS columns
desc = {}
for c in psq_n.columns:
    desc[c] = describe(psq_n[c], psq_ranges[c])
for c in tics_n.columns:
    desc[c] = describe(tics_n[c], None)
report["descriptives"] = desc

# Check whether PSQ_OverallScore equals mean of the four subscales (calculation is UNCLEAR, so this is a test, not an assumption)
sub = psq_n[["PSQ_Worries", "PSQ_Tension", "PSQ_Joy", "PSQ_Demands"]].apply(pd.to_numeric, errors="coerce")
mean4 = sub.mean(axis=1)
overall = pd.to_numeric(psq_n["PSQ_OverallScore"], errors="coerce")
both = pd.concat([overall, mean4], axis=1).dropna()
report["PSQ_overall_vs_mean_of_subscales"] = {
    "n_compared": int(len(both)),
    "n_within_0.01": int(((both.iloc[:, 0] - both.iloc[:, 1]).abs() <= 0.01).sum()),
    "max_abs_difference": round(float((both.iloc[:, 0] - both.iloc[:, 1]).abs().max()), 3),
}

# TICS: check whether the file has a total column and whether ScreeningScale equals the sum of the 9 subscales
tics_subs = [c for c in tics_n.columns if c not in ("TICS_ScreeningScale",)]
tics_num = tics_n[tics_subs].apply(pd.to_numeric, errors="coerce")
tot_sum = tics_num.sum(axis=1, min_count=len(tics_subs))
scr = pd.to_numeric(tics_n["TICS_ScreeningScale"], errors="coerce")
both2 = pd.concat([scr, tot_sum], axis=1).dropna()
report["TICS_screening_vs_sum_of_subscales"] = {
    "n_compared": int(len(both2)),
    "n_equal": int(((both2.iloc[:, 0] - both2.iloc[:, 1]).abs() < 1e-9).sum()),
    "example_first_row_screening": float(both2.iloc[0, 0]) if len(both2) else None,
    "example_first_row_sum": float(both2.iloc[0, 1]) if len(both2) else None,
}

# ---- Step 7: clean CSV (no deletion, no imputation) ----
clean = pd.DataFrame(index=sorted(set(psq_n.index) | set(tics_n.index)))
clean.index.name = "ID"
for c in psq_n.columns:
    clean[c] = pd.to_numeric(psq_n[c], errors="coerce").reindex(clean.index)
for c in tics_n.columns:
    clean[c] = pd.to_numeric(tics_n[c], errors="coerce").reindex(clean.index)
clean.reset_index().to_csv(os.path.join(OUT, "stress_clean.csv"), index=False)
report["clean_rows"] = int(len(clean))
report["clean_columns"] = list(clean.columns)

# ---- Step 4: histograms of the main score of each questionnaire ----
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].hist(pd.to_numeric(psq_n["PSQ_OverallScore"], errors="coerce").dropna(), bins=20, color="#4C72B0")
ax[0].set_title("PSQ_OverallScore (values as stored in PSQ.csv)")
ax[0].set_xlabel("score"); ax[0].set_ylabel("participants")
ax[1].hist(scr.dropna(), bins=20, color="#DD8452")
ax[1].set_title("TICS_ScreeningScale (no total column found)")
ax[1].set_xlabel("score"); ax[1].set_ylabel("participants")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "histograms_main_scores.png"), dpi=120)
plt.close()

# ---- Step 8: correlations (PSQ total vs TICS; TICS total is absent, so two proxies are reported) ----
from scipy import stats
psq_total = pd.to_numeric(psq_n["PSQ_OverallScore"], errors="coerce")
corr = {}
for label, tv in [("TICS_ScreeningScale", scr), ("sum_of_9_TICS_subscales (computed here)", tot_sum)]:
    pair = pd.concat([psq_total, tv], axis=1).dropna()
    if len(pair) > 2:
        r, p = stats.pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
        rho, pr = stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
        corr[label] = {"n": int(len(pair)), "pearson_r": round(r, 3), "pearson_p": float(f"{p:.3g}"),
                       "spearman_rho": round(rho, 3), "spearman_p": float(f"{pr:.3g}")}
report["correlations_PSQ_overall_vs_TICS"] = corr

with open(os.path.join(OUT, "task2_checks.json"), "w") as f:
    json.dump(report, f, indent=2, default=str)
print(json.dumps(report, indent=2, default=str))
