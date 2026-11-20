"""Independent exploratory analysis; no model fitting or train/test allocation."""

import itertools
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
SOURCE = ROOT / "data/lemon/source"
BEHAVIOR = SOURCE / "Behavioural_Data_MPILMBB_LEMON"
OUT = ROOT / "data/derived/dataset_overview"
BLOOD = ["GLU_in_mmol_l", "HBA1CI_in_mmol_mol", "LDLC_in_mmol_l",
         "HDLC_in_mmol_l", "CHOL_in_mmol_l", "TRIG_in_mmol_l", "CKDEPI_in_ml_min_1.73m"]
COGNITION = ["CVLT_6", "CVLT_11", "LPS_1", "TMT_1", "TMT_5", "WST_1", "RWT_8", "RWT_20"]
LABELS = {"GLU_in_mmol_l": "Glucose (mmol/L)", "HBA1CI_in_mmol_mol": "HbA1c (mmol/mol)",
          "LDLC_in_mmol_l": "LDL cholesterol (mmol/L)", "HDLC_in_mmol_l": "HDL cholesterol (mmol/L)",
          "CHOL_in_mmol_l": "Total cholesterol (mmol/L)", "TRIG_in_mmol_l": "Triglycerides (mmol/L)",
          "CKDEPI_in_ml_min_1.73m": "CKD-EPI eGFR (mL/min/1.73 m²)",
          "CVLT_6": "CVLT learning total (words, trials 1–5)",
          "CVLT_11": "CVLT long-delay free recall (words)", "LPS_1": "LPS correct rows",
          "TMT_1": "Trail Making A (s)", "TMT_5": "Trail Making B (s)",
          "WST_1": "Vocabulary correct words", "RWT_8": "S-word fluency (2 min)",
          "RWT_20": "Animal fluency (2 min)"}


def read(path):
    separator = ";" if "Follo-up" in path.name else ","
    frame = pd.read_csv(path, sep=separator, dtype=str, encoding="utf-8-sig")
    if separator == ";":
        frame = frame.rename(columns={frame.columns[0]: "ID"})
        frame = frame.drop(columns=[c for c in frame if c.startswith("Unnamed:")])
    return frame


def numeric(series):
    return pd.to_numeric(series.str.strip().str.replace(",", ".", regex=False), errors="coerce")


def unique_table(frame, name, issues):
    if "ID" not in frame:
        raise ValueError(f"Missing ID column in {name}")
    frame = frame.copy()
    normalized = frame.ID.str.replace(r"^Sub-", "sub-", regex=True).str.strip()
    changed_ids = int(frame.ID.ne(normalized).sum())
    frame["ID"] = normalized
    valid = frame.ID.str.fullmatch(r"sub-\d{6}", na=False)
    duplicates = frame.ID.duplicated(keep=False)
    issues.append({"table": name, "rows": len(frame), "unique_ids": frame.loc[valid, "ID"].nunique(),
                   "normalized_id_rows": changed_ids, "invalid_id_rows": int((~valid).sum()), "ambiguous_duplicate_rows": int(duplicates.sum()),
                   "ambiguous_duplicate_ids": int(frame.loc[duplicates, "ID"].nunique())})
    return frame.loc[valid & ~duplicates].set_index("ID")


def bh(values):
    return stats.false_discovery_control(np.asarray(values), method="bh")


def codebook(path, columns):
    candidates = [p for p in path.parent.iterdir() if p.is_file() and p.suffix != ".csv"]
    text = "\n".join(p.read_text(encoding="utf-8-sig", errors="replace") for p in candidates)
    definitions = {}
    for line in text.splitlines():
        line = line.strip().lstrip("\ufeff")
        if "=" in line:
            key, definition = line.split("=", 1)
            definitions[key.strip()] = definition.strip()
        if ":" in line:
            key, definition = line.split(":", 1)
            definitions[key.strip()] = definition.strip()
    for info in (BEHAVIOR / "Data_Availability_Tables").glob("*Info"):
        for line in info.read_text(errors="replace").splitlines():
            if ":" in line:
                key, definition = line.strip().split(":", 1)
                definitions.setdefault(key.strip(), definition.strip())
    if path.name == "Blood_Results_LEMON.csv":
        for line in text.splitlines():
            match = re.match(r"^(\d+)[.:]\s*(.+)$", line.strip())
            if match and 1 <= int(match[1]) <= len(columns):
                definitions[columns[int(match[1])-1]] = match[2]
    result = {}
    for column in columns:
        if column == "ID":
            result[column] = "Pseudonymous public BIDS participant identifier"
        elif column in definitions:
            result[column] = definitions[column]
        elif column.startswith("CVLT_") and column.split("_")[-1] in definitions:
            result[column] = definitions[column.split("_")[-1]]
        elif column in LABELS:
            result[column] = LABELS[column]
        else:
            # Keep the original variable name and link the source, without inventing a definition.
            result[column] = "See source codebook; meaning not automatically resolved"
        if "Data_Availability_Tables" in str(path) and column != "ID":
            result[column] = "Availability indicator (1 available, 0 unavailable): " + result[column]
    return result, ";".join(str(p.relative_to(ROOT)) for p in candidates)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)
    issues, dictionary, file_counts = [], [], []
    meta = read(next(BEHAVIOR.glob("META*.csv")))
    master = unique_table(meta, "demographics", issues)
    ids = master.index
    master["age_bin"] = master.Age
    master["age_group"] = np.where(master.Age.str.split("-").str[0].astype(int) < 40, "young", "older")
    # Derived midpoint is explicitly approximate, never exact participant age.
    master["age_bin_midpoint_approx"] = master.Age.map(lambda x: np.mean([int(v) for v in x.split("-")]))
    master["sex_code"] = numeric(master["Gender_ 1=female_2=male"])
    master["alcohol_units_28days"] = numeric(master.Standard_Alcoholunits_Last_28days)
    master["education_clean"] = master.Education.replace({"Gymansium": "Gymnasium"})
    allowed = ["Gymnasium", "Realschule", "Hauptschule", "none (Hauptschule not finished)"]
    master.loc[~master.education_clean.isin(allowed), "education_clean"] = pd.NA
    raw_inventory = pd.read_csv(SOURCE / "remote_inventory.csv")
    remote = raw_inventory.loc[~raw_inventory.directory].copy()
    remote["ID"] = remote.relative_path.str.extract(r"(sub-\d{6})")[0]
    flags = {
        "mri_t1_remote": r"MRI_Raw/.+_T1w\.nii\.gz$",
        "mri_t2_remote": r"MRI_Raw/.+_T2w\.nii\.gz$",
        "mri_flair_remote": r"MRI_Raw/.+_FLAIR\.nii\.gz$",
        "mri_dwi_remote": r"MRI_Raw/.+_dwi\.nii\.gz$",
        "mri_bold_remote": r"MRI_Raw/.+_bold\.nii\.gz$",
        "eeg_eo_set_remote": r"EEG_Preprocessed/.+_EO\.set$",
        "eeg_eo_fdt_remote": r"EEG_Preprocessed/.+_EO\.fdt$",
        "eeg_ec_set_remote": r"EEG_Preprocessed/.+_EC\.set$",
        "eeg_ec_fdt_remote": r"EEG_Preprocessed/.+_EC\.fdt$",
        "eeg_raw_signal_remote": r"EEG_Raw_BIDS_ID/.+\.eeg$",
        "eeg_raw_header_remote": r"EEG_Raw_BIDS_ID/.+\.vhdr$",
        "eeg_raw_markers_remote": r"EEG_Raw_BIDS_ID/.+\.vmrk$",
        "physiology_ses01_remote": r"MRI_PERPHYS_joined/.+/ses-01/func/.+\.tsv\.gz$",
    }
    for flag, pattern in flags.items():
        subset = remote[remote.relative_path.str.contains(pattern, regex=True)]
        master[flag] = ids.isin(subset.ID)
        file_counts.append({"modality": flag, "remote_files": len(subset), "unique_ids": subset.ID.nunique()})
    master["eeg_eo_remote"] = master.eeg_eo_set_remote & master.eeg_eo_fdt_remote
    master["eeg_ec_remote"] = master.eeg_ec_set_remote & master.eeg_ec_fdt_remote
    master["eeg_both_conditions_remote"] = master.eeg_eo_remote & master.eeg_ec_remote
    master["eeg_raw_triple_remote"] = master.eeg_raw_signal_remote & master.eeg_raw_header_remote & master.eeg_raw_markers_remote
    for flag, prefix in [("eeg_raw_directory", "EEG_MPILMBB_LEMON/EEG_Raw_BIDS_ID/"),
                         ("mri_derivative_directory", "MRI_MPILMBB_LEMON/MRI_Preprocessed_Derivetives/")]:
        rows = raw_inventory[raw_inventory.directory & raw_inventory.relative_path.str.startswith(prefix)]
        master[flag] = ids.isin(rows.relative_path.str.extract(r"(sub-\d{6})")[0])
    files = sorted(BEHAVIOR.rglob("*.csv"))
    analysis_variables = []
    for path in files:
        frame = read(path)
        # Some source tables contain blank or unnamed ID columns; inventory them, never join implicitly.
        descriptions, info_path = codebook(path, frame.columns)
        for column in frame.columns:
            s = frame[column]
            n = numeric(s)
            dictionary.append({"source_file": str(path.relative_to(ROOT)), "variable": column,
                               "description": descriptions[column], "source_codebook": info_path,
                               "records": len(frame), "present_cells": int(s.notna().sum()),
                               "missing_cells": int(s.isna().sum()), "numeric_cells": int(n.notna().sum()),
                               "censored_cells": int(s.str.match(r"\s*[<>]", na=False).sum()),
                               "unique_values": int(s.nunique()),
                               "reference_range": "reference" in column.lower() or "rerefence" in column.lower()})
        if "ID" not in frame:
            issues.append({"table": str(path.relative_to(BEHAVIOR)), "rows": len(frame), "note": "No ID header; inventoried only"})
            continue
        table = unique_table(frame, str(path.relative_to(BEHAVIOR)), issues)
        if "Data_Availability" in str(path):
            reported = pd.DataFrame({f"reported::{column}": numeric(table[column]).reindex(ids) for column in table})
            master = master.join(reported, validate="one_to_one")
            continue
        is_blood = path.name == "Blood_Results_LEMON.csv"
        is_cognition = "Cognitive_Test_Battery" in str(path)
        is_physiology = path.name in ("Anthropometry_LEMON.csv", "Blood_Pressure_LEMON.csv")
        if not (is_blood or is_cognition or is_physiology):
            continue
        columns = [c for c in table if not re.search(r"reference|rerefence|date", c, re.I)]
        values = pd.DataFrame({c: numeric(table[c]) for c in columns})
        if is_cognition:
            columns = [c for c in columns if c in COGNITION or c in (
                "TAP_A_5", "TAP_A_10", "TAP_I_1", "TAP_I_8", "TAP_WM_1", "TAP_WM_6", "TAP_WM_7", "TAP_WM_9")]
        master = master.join(values[columns], validate="one_to_one")
        analysis_variables.extend(columns)
        flag = "blood_any_numeric" if is_blood else (path.stem + "_any_numeric")
        master[flag] = values[columns].reindex(ids).notna().any(axis=1)
        if is_blood:
            master["blood_core7_complete"] = values[BLOOD].reindex(ids).notna().all(axis=1)
    master["BMI"] = master.Weight_kg / (master.Height_cm / 100) ** 2
    analysis_variables.append("BMI")
    master["cognition_primary_available"] = master.TMT_5.notna()
    master.to_csv(OUT / "participant_master.csv", index_label="ID")
    pd.DataFrame(dictionary).to_csv(OUT / "variable_dictionary.csv", index=False)
    pd.DataFrame(issues).to_csv(OUT / "source_table_quality.csv", index=False)
    pd.DataFrame(file_counts).to_csv(OUT / "remote_modality_counts.csv", index=False)
    summary, outliers = [], []
    for column in analysis_variables:
        for group in ("all", "young", "older"):
            s = master[column] if group == "all" else master.loc[master.age_group.eq(group), column]
            present = s.dropna()
            if present.empty:
                continue
            q1, q3 = present.quantile([0.25, 0.75])
            flags_out = (s < q1 - 1.5 * (q3 - q1)) | (s > q3 + 1.5 * (q3 - q1))
            summary.append({"variable": column, "group": group, "denominator": len(s), "n": len(present),
                            "missing_pct": 100 * s.isna().mean(), "mean": present.mean(), "median": present.median(),
                            "std": present.std(), "min": present.min(), "max": present.max(),
                            "q1": q1, "q3": q3, "iqr_flag_count": int(flags_out.sum())})
            if group == "all":
                outliers.extend({"ID": p, "variable": column, "value": s[p], "rule": "1.5 IQR; retained"}
                                for p in s.index[flags_out])
    pd.DataFrame(summary).to_csv(OUT / "descriptive_statistics.csv", index=False)
    pd.DataFrame(outliers).to_csv(OUT / "outlier_flags.csv", index=False)
    selected = BLOOD + COGNITION
    confounds = pd.concat([
        pd.get_dummies(master[["age_bin", "education_clean"]], drop_first=True, dtype=float),
        master[["sex_code", "BMI", "alcohol_units_28days"]]], axis=1)
    confounds.loc[master.education_clean.isna(), :] = np.nan
    correlations = []
    for x, y in itertools.product(BLOOD, COGNITION):
        for method in ("pearson", "spearman", "partial_pearson"):
            pair = master[[x, y]].dropna()
            rank_covariates = 0
            if method == "partial_pearson":
                pair = master[[x, y]].join(confounds).dropna()
                design = np.column_stack([np.ones(len(pair)), pair[confounds.columns].to_numpy(float)])
                rank_covariates = np.linalg.matrix_rank(design) - 1
                residuals = pair[[x, y]].to_numpy(float) - design @ np.linalg.lstsq(design, pair[[x, y]].to_numpy(float), rcond=None)[0]
                r = np.corrcoef(residuals.T)[0, 1]
                df = len(pair) - rank_covariates - 2
                p = 2 * stats.t.sf(abs(r) * np.sqrt(df / (1 - r*r)), df) if df > 0 else np.nan
            else:
                result = (stats.pearsonr if method == "pearson" else stats.spearmanr)(pair[x], pair[y])
                r, p = result.statistic, result.pvalue
            correlations.append({"x": x, "y": y, "method": method, "n": len(pair), "r": r,
                                 "p": p, "covariate_rank": rank_covariates})
    corr = pd.DataFrame(correlations)
    corr["q_bh"] = corr.groupby("method").p.transform(lambda p: bh(p))
    corr.to_csv(OUT / "biomarker_cognition_correlations.csv", index=False)
    within = []
    for group in ("young", "older"):
        for x, y in itertools.product(BLOOD, COGNITION):
            pair = master.loc[master.age_group.eq(group), [x, y]].dropna()
            r, p = stats.spearmanr(pair[x], pair[y])
            within.append({"group": group, "x": x, "y": y, "n": len(pair), "r": r, "p": p})
    within = pd.DataFrame(within)
    within["q_bh"] = bh(within.p)
    within.to_csv(OUT / "within_group_spearman.csv", index=False)
    comparisons = []
    for variable in selected:
        young = master.loc[master.age_group.eq("young"), variable].dropna()
        older = master.loc[master.age_group.eq("older"), variable].dropna()
        result = stats.ttest_ind(young, older, equal_var=False)
        comparisons.append({"variable": variable, "young_n": len(young), "older_n": len(older),
                            "older_minus_young_mean": older.mean() - young.mean(), "t": result.statistic, "p": result.pvalue})
    comparisons = pd.DataFrame(comparisons)
    comparisons["q_bh"] = bh(comparisons.p)
    comparisons.to_csv(OUT / "age_group_comparisons.csv", index=False)
    availability = ["mri_t1_remote", "mri_t2_remote", "mri_dwi_remote", "mri_bold_remote", "eeg_raw_triple_remote", "eeg_eo_remote",
                    "eeg_ec_remote", "eeg_both_conditions_remote", "blood_any_numeric", "blood_core7_complete", "cognition_primary_available"]
    overlap = pd.DataFrame([[int((master[a] & master[b]).sum()) for b in availability] for a in availability],
                           index=availability, columns=availability)
    overlap.to_csv(OUT / "modality_overlap.csv")
    summary_json = {
        "canonical_participants": len(master), "age_groups": master.age_group.value_counts().to_dict(),
        "age_bins": master.age_bin.value_counts().to_dict(),
        "availability": {c: int(master[c].sum()) for c in availability},
        "t1_eeg_eo_core7_tmtb_overlap": int(master[["mri_t1_remote", "eeg_eo_remote", "blood_core7_complete", "cognition_primary_available"]].all(axis=1).sum()),
        "fdr_discoveries_by_method": corr.assign(discovery=corr.q_bh < 0.05).groupby("method").discovery.sum().to_dict(),
        "within_group_fdr_discoveries": int((within.q_bh < 0.05).sum()),
        "raw_mri_listing_errors": json.loads((SOURCE / "fetch_manifest.json").read_text())["errors"],
        "status": "Exploratory full-cohort tabular analysis; no reserved test cohort; no models trained"}
    (OUT / "summary.json").write_text(json.dumps(summary_json, indent=2))
    branches = remote.assign(branch=remote.relative_path.str.split("/").str[0]).groupby("branch").agg(
        files=("relative_path", "size"), listed_bytes=("listed_bytes", "sum"))
    branches.to_csv(OUT / "archive_branch_inventory.csv")
    remote.assign(extension=remote.relative_path.str.extract(r"(\.nii\.gz|\.[^.\/]+)$")[0]).groupby(
        "extension").size().rename("files").to_csv(OUT / "archive_format_counts.csv")
    mismatches = []
    for actual, reported in [("mri_t1_remote", "MP2RAGE"), ("mri_dwi_remote", "DWI"),
                             ("mri_bold_remote", "rs-fMRI"), ("eeg_raw_triple_remote", "EEG_RestingState_Raw"),
                             ("eeg_both_conditions_remote", "EEG_Preprocessed")]:
        expected = master[f"reported::{reported}"]
        for participant in master.index[expected.notna() & master[actual].ne(expected.eq(1))]:
            mismatches.append({"ID": participant, "actual_flag": actual, "remote_listing": bool(master.loc[participant, actual]),
                               "reported_available": bool(expected.loc[participant] == 1)})
    pd.DataFrame(mismatches).to_csv(OUT / "availability_discrepancies.csv", index=False)
    plot_distributions(master, BLOOD, "biomarker_distributions")
    plot_distributions(master, COGNITION, "cognitive_distributions")
    plot_boxes(master, selected)
    fig, ax = plt.subplots(figsize=(12, 6), layout="constrained")
    missing = master[analysis_variables].isna().mean().mul(100).sort_values(ascending=False).head(25)
    ax.barh(missing.index[::-1], missing.values[::-1], color="#327c98")
    ax.set(xlabel="Missing or excluded non-numeric values (%)", title="Highest missingness among analysis variables (N=227)")
    fig.savefig(OUT / "figures/missingness.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), layout="constrained")
    for ax, method in zip(axes, ("spearman", "partial_pearson")):
        subset = corr[corr.method.eq(method)]
        matrix = subset.pivot(index="x", columns="y", values="r").reindex(index=BLOOD, columns=COGNITION)
        q = subset.pivot(index="x", columns="y", values="q_bh").reindex(index=BLOOD, columns=COGNITION)
        im = ax.imshow(matrix, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
        ax.set_xticks(range(len(COGNITION)), COGNITION, rotation=65, ha="right")
        ax.set_yticks(range(len(BLOOD)), [LABELS[c].split(" (")[0] for c in BLOOD])
        ax.set_title(method.replace("_", " ") + "; * BH q<0.05 (56 tests)")
        for i, j in itertools.product(range(len(BLOOD)), range(len(COGNITION))):
            ax.text(j, i, f"{matrix.iloc[i,j]:.2f}" + ("*" if q.iloc[i,j] < .05 else ""), ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=axes, label="Correlation coefficient")
    fig.savefig(OUT / "figures/biomarker_cognition_heatmap.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), layout="constrained")
    for ax, x in zip(axes, [BLOOD[1], BLOOD[2], BLOOD[-1]]):
        for group, color in [("young", "#2781a0"), ("older", "#c26836")]:
            subset = master[master.age_group.eq(group)]
            ax.scatter(subset[x], subset.TMT_5, label=group, s=18, alpha=.55, color=color)
        ax.set(xlabel=LABELS[x], ylabel=LABELS["TMT_5"])
    axes[0].legend()
    fig.suptitle("Exploratory participant-level associations; age groups may confound pooled patterns")
    fig.savefig(OUT / "figures/biomarkers_tmtb_scatter.png", dpi=160); plt.close(fig)
    print(json.dumps(summary_json, indent=2))


def plot_distributions(master, variables, filename):
    fig, axes = plt.subplots(2, 4, figsize=(15, 7), layout="constrained")
    for ax, column in zip(axes.flat, variables):
        for group, color in [("young", "#2781a0"), ("older", "#c26836")]:
            values = master.loc[master.age_group.eq(group), column].dropna()
            ax.hist(values, bins="auto", density=True, alpha=.4, color=color, label=f"{group} n={len(values)}")
            if column in BLOOD and values.nunique() > 10:
                grid = np.linspace(values.min(), values.max(), 200)
                ax.plot(grid, stats.gaussian_kde(values)(grid), color=color, linewidth=1)
        ax.set(xlabel=LABELS[column], ylabel="Density")
        ax.legend(fontsize=8)
    for ax in list(axes.flat)[len(variables):]:
        ax.set_visible(False)
    fig.suptitle("Independent EDA; histograms use observed numeric values; curves are descriptive KDEs")
    fig.savefig(OUT / f"figures/{filename}.png", dpi=160); plt.close(fig)


def plot_boxes(master, variables):
    for kind in ("box", "violin"):
        fig, axes = plt.subplots(3, 5, figsize=(17, 10), layout="constrained")
        for ax, column in zip(axes.flat, variables):
            values = [master.loc[master.age_group.eq(g), column].dropna().to_numpy() for g in ("young", "older")]
            if kind == "box":
                ax.boxplot(values, tick_labels=["young", "older"], flierprops={"markersize": 3})
            else:
                ax.violinplot(values, showmedians=True, showextrema=True)
                ax.set_xticks([1, 2], ["young", "older"])
            ax.set_title(LABELS[column], fontsize=9)
        fig.suptitle(f"Age-group {kind} plots; all observations retained; no diagnostic thresholds")
        fig.savefig(OUT / f"figures/{kind}_plots.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
