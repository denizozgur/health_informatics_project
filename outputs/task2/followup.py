import json
import numpy as np
import pandas as pd
from scipy import stats

IN = "/mnt/user-data/outputs/task2/stress_clean.csv"
OUT = "/mnt/user-data/outputs/task2"
df = pd.read_csv(IN)
res = {"input_file": IN, "rows": int(len(df))}

# ---- 1. OverallScore vs mean(Worries, Tension, Demands, 100 - Joy) ----
d = df.dropna(subset=["PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "PSQ_Joy", "PSQ_OverallScore"]).copy()
d["joy_reversed"] = 100 - d["PSQ_Joy"]
d["mean_4_reversed_joy"] = d[["PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "joy_reversed"]].mean(axis=1)
d["gap"] = (d["PSQ_OverallScore"] - d["mean_4_reversed_joy"]).abs()
res["test1"] = {
    "rows_with_all_five_values": int(len(d)),
    "n_within_0.01": int((d["gap"] <= 0.01).sum()),
    "largest_gap": round(float(d["gap"].max()), 4),
    "median_gap": round(float(d["gap"].median()), 4),
    "mean_signed_difference_overall_minus_mean": round(float((d["PSQ_OverallScore"] - d["mean_4_reversed_joy"]).mean()), 4),
    "pearson_r_overall_vs_mean": round(float(np.corrcoef(d["PSQ_OverallScore"], d["mean_4_reversed_joy"])[0, 1]), 4),
    "ids_with_largest_gap_top5": d.sort_values("gap", ascending=False)["ID"].head(5).tolist(),
}

# Also test the simpler version without reversing joy, so the direction question is answered by data
d["mean_4_raw_joy"] = d[["PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "PSQ_Joy"]].mean(axis=1)
d["gap_raw"] = (d["PSQ_OverallScore"] - d["mean_4_raw_joy"]).abs()
res["test1_alt_joy_not_reversed"] = {
    "n_within_0.01": int((d["gap_raw"] <= 0.01).sum()),
    "largest_gap": round(float(d["gap_raw"].max()), 4),
    "pearson_r": round(float(np.corrcoef(d["PSQ_OverallScore"], d["mean_4_raw_joy"])[0, 1]), 4),
}

# ---- 2. Correlation with and without sub-010134 ----
pair = df[["ID", "PSQ_OverallScore", "TICS_ScreeningScale"]].dropna()
def corr_block(p):
    r, pv = stats.pearsonr(p["PSQ_OverallScore"], p["TICS_ScreeningScale"])
    rho, pr = stats.spearmanr(p["PSQ_OverallScore"], p["TICS_ScreeningScale"])
    return {"n": int(len(p)), "pearson_r": round(r, 3), "pearson_p": float(f"{pv:.3g}"),
            "spearman_rho": round(rho, 3), "spearman_p": float(f"{pr:.3g}")}
res["test2_all"] = corr_block(pair)
res["test2_excluding_sub-010134"] = corr_block(pair[pair["ID"] != "sub-010134"])
res["test2_sub-010134_values"] = pair[pair["ID"] == "sub-010134"].to_dict("records")

with open(f"{OUT}/followup_checks.json", "w") as f:
    json.dump(res, f, indent=2)
d[["ID", "PSQ_OverallScore", "PSQ_Worries", "PSQ_Tension", "PSQ_Demands", "PSQ_Joy", "joy_reversed",
   "mean_4_reversed_joy", "gap", "mean_4_raw_joy", "gap_raw"]].to_csv(f"{OUT}/followup_test1_rows.csv", index=False)
print(json.dumps(res, indent=2))
