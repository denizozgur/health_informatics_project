"""Match PSQ to archived resting BOLD and ECG files before signal QC."""

import csv
import re
from statistics import mean, median, stdev

if __package__:
    from . import lemon_psychology_eda as psq_eda
else:
    import lemon_psychology_eda as psq_eda

RUN = re.compile(r"/(sub-\d{6})/ses-01/func/\1_ses-01_task-rest_acq-AP_run-01(?P<suffix>_.+)$")
FILES = {
    ("MRI_Raw", "_bold.nii.gz"): "bold_path",
    ("MRI_Raw", "_bold.json"): "bold_json_path",
    ("MRI_PERPHYS_joined", "_recording-ecg_physio.tsv.gz"): "ecg_path",
    ("MRI_PERPHYS_joined", "_recording-ecg_physio.json"): "ecg_json_path",
}


def read_runs():
    runs = {}
    with psq_eda.INVENTORY.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            path = row["relative_path"]
            match = RUN.search(path)
            if row["directory"].strip().casefold() not in {"false", "0"} or match is None:
                continue
            branch = path[:match.start()].rsplit("/", 1)[-1]
            field = FILES.get((branch, match["suffix"]))
            if field:
                files = runs.setdefault(match[1], {})
                if field in files and files[field] != path:
                    raise ValueError(f"Ambiguous {field} for {match[1]}")
                files[field] = path
    if not runs:
        raise ValueError(f"No matching session-01 run-01 files in {psq_eda.INVENTORY}")
    return runs


def summarize(label, participants, scores, demographics):
    valid = [scores[participant] for participant in participants if scores[participant] is not None]
    rows = [demographics[participant] for participant in participants]
    age_groups = [psq_eda.age_group(row["Age"]) for row in rows]
    return {
        "cohort": label, "n": len(participants), "psq_n": len(valid),
        "psq_missing_or_invalid_n": len(participants) - len(valid),
        "psq_mean": mean(valid) if valid else None,
        "psq_sd": stdev(valid) if len(valid) > 1 else None,
        "psq_median": median(valid) if valid else None,
        "younger_n": age_groups.count("younger"),
        "older_n": age_groups.count("older"),
        "female_n": sum(row[psq_eda.SEX] == "1" for row in rows),
        "male_n": sum(row[psq_eda.SEX] == "2" for row in rows),
    }


def main():
    demographics = psq_eda.read_demographics()
    psq_totals = psq_eda.read_psq_totals()
    runs = read_runs()
    all_ids = set(demographics)
    scores = {pid: psq_totals.get(pid) for pid in demographics}
    psq_ids = {pid for pid, score in scores.items() if score is not None}
    bold = {pid for pid in all_ids if "bold_path" in runs.get(pid, {})}
    ecg = {pid for pid in all_ids if "ecg_path" in runs.get(pid, {})}
    matched = bold & ecg
    candidate = psq_ids & matched
    with_sidecars = {pid for pid in candidate if set(FILES.values()) <= runs[pid].keys()}
    cohorts = {
        "all_demographic_ids": all_ids, "valid_psq": psq_ids, "bold": bold, "ecg": ecg,
        "matched_bold_ecg": matched, "psq_matched_bold_ecg": candidate,
        "psq_matched_bold_ecg_with_both_sidecars": with_sidecars,
        "valid_psq_without_matched_bold_ecg": psq_ids - matched,
    }
    psq_eda.write_csv(psq_eda.OTHER_OUT / "psq_bold_ecg_cohorts.csv", [
        summarize(label, participants, scores, demographics) for label, participants in cohorts.items()
    ])
    psq_eda.write_csv(psq_eda.OTHER_OUT / "psq_bold_ecg_candidates.csv", [
        {"ID": pid, **{field: runs[pid].get(field, "") for field in FILES.values()}}
        for pid in sorted(candidate)
    ], fieldnames=["ID", *FILES.values()])
    print(f"{len(candidate)} candidates with PSQ, BOLD and ECG ({len(with_sidecars)} with both JSON sidecars)")


if __name__ == "__main__":
    main()
