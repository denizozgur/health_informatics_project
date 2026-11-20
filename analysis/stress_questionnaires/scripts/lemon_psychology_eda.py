"""Summarize the LEMON psychological test battery and published PSQ scores (teammate's script).

    uv run python -m analysis.stress_questionnaires.scripts.lemon_psychology_eda

Reads the behavioural data from data/lemon/source/Behavioural_Data_MPILMBB_LEMON (layout made by
data_download/fetch_lemon.py) or, if that is missing, from data/LEMON. Group-level tables go to
analysis/stress_questionnaires/results/; the copy of PSQ.csv goes to data/derived/stress_questionnaires/.
"""

import csv
import math
import re
import warnings
from collections import Counter
from pathlib import Path
from shutil import copyfile
from statistics import mean, median, quantiles, stdev

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/lemon/source"
INVENTORY = SOURCE / "remote_inventory.csv"
BEHAVIOR = SOURCE / "Behavioural_Data_MPILMBB_LEMON"
if not BEHAVIOR.exists():          # this project's download layout
    BEHAVIOR = ROOT / "data/LEMON"
BATTERY = BEHAVIOR / "Emotion_and_Personality_Test_Battery_LEMON"
DEMOGRAPHICS = BEHAVIOR / "META_File_IDs_Age_Gender_Education_Drug_Smoke_SKID_LEMON.csv"
OUT = ROOT / "analysis/stress_questionnaires/results"
OTHER_OUT = OUT
PRIVATE = ROOT / "data/derived/stress_questionnaires"
PSQ_FILE = BATTERY / "PSQ.csv"
PSQ_COLUMNS = ("PSQ_OverallScore", "PSQ_Worries", "PSQ_Tension", "PSQ_Joy", "PSQ_Demands")
OVERALL = PSQ_COLUMNS[0]
SEX = "Gender_ 1=female_2=male"
MISSING_VALUES = {"", "n/a", "na", "nan", "-", "--", "null"}


def clean_value(raw):
    value = (raw or "").strip()
    return "" if value.casefold() in MISSING_VALUES else value


def read_table(path, *, required=()):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = [column.strip() for column in (reader.fieldnames or [])]
        if "ID" not in headers:
            raise ValueError(f"{path}: missing ID column")
        if len(headers) != len(set(headers)):
            raise ValueError(f"{path}: duplicate headers after trimming whitespace")
        missing = set(required) - set(headers)
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        reader.fieldnames = headers
        columns = [column for column in headers if column != "ID"]
        rows = list(reader)

    ids = [clean_value(row.get("ID")).lower() for row in rows]
    counts = Counter(ids)
    table = {
        participant: {column: clean_value(row.get(column)) for column in columns}
        for participant, row in zip(ids, rows, strict=True)
        if re.fullmatch(r"sub-\d{6}", participant) and counts[participant] == 1
    }
    return columns, table, len(rows)


def age_group(value):
    age_bin = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", value)
    if age_bin:
        lower, upper = map(int, age_bin.groups())
        if lower < upper <= 40:
            return "younger"
        if 40 <= lower < upper:
            return "older"
    return None


def read_demographics():
    _, table, source_rows = read_table(DEMOGRAPHICS, required=("Age", SEX))
    discarded = source_rows - len(table)
    if discarded:
        warnings.warn(f"{DEMOGRAPHICS.name}: excluded {discarded} rows with invalid or duplicate IDs")
    ungrouped = sum(age_group(row["Age"]) is None for row in table.values())
    if ungrouped:
        warnings.warn(f"{DEMOGRAPHICS.name}: {ungrouped} participants could not be assigned an age group")
    return table


def parse_score(raw):
    if raw:
        try:
            score = float(raw.replace(",", "."))
        except ValueError:
            return None
        if math.isfinite(score) and 0 <= score <= 100:
            return score
    return None


def read_psq():
    return read_table(PSQ_FILE, required=PSQ_COLUMNS)


def read_psq_totals():
    """Map each PSQ participant ID to a valid total score or None."""
    _, participants, _ = read_psq()
    return {participant_id: parse_score(row[OVERALL]) for participant_id, row in participants.items()}


def participant_groups(demographics):
    groups = {"all": list(demographics), "younger": [], "older": [], "female": [], "male": []}
    for participant, row in demographics.items():
        group = age_group(row["Age"])
        if group:
            groups[group].append(participant)
        sex = {"1": "female", "2": "male"}.get(row[SEX])
        if sex:
            groups[sex].append(participant)
    return groups


def describe(column, participants, psq, group):
    raw = [psq.get(participant, {}).get(column, "") for participant in participants]
    parsed = [parse_score(value) for value in raw]
    scores = [score for score in parsed if score is not None]
    q1 = q3 = None
    flags = 0
    if len(scores) > 1:
        q1, _, q3 = quantiles(scores, n=4, method="inclusive")
        iqr = q3 - q1
        flags = sum(score < q1 - 1.5 * iqr or score > q3 + 1.5 * iqr for score in scores)
    return {
        "score": column,
        "group": group,
        "cohort_n": len(participants),
        "valid_n": len(scores),
        "missing_n": raw.count(""),
        "invalid_n": sum(bool(value) and score is None for value, score in zip(raw, parsed, strict=True)),
        "mean": mean(scores) if scores else None,
        "sd": stdev(scores) if len(scores) > 1 else None,
        "min": min(scores) if scores else None,
        "q1": q1,
        "median": median(scores) if scores else None,
        "q3": q3,
        "max": max(scores) if scores else None,
        "iqr_flag_n": flags,
    }


def write_csv(path, rows, *, fieldnames=None):
    if fieldnames is None:
        if not rows:
            raise ValueError(f"{path}: fieldnames are required when rows is empty")
        fieldnames = list(rows[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def questionnaire_coverage(demographics, psq_source):
    inventory = []
    for path in sorted(BATTERY.glob("*.csv")):
        is_psq = path == PSQ_FILE
        try:
            columns, table, source_rows = psq_source if is_psq else read_table(path)
        except (ValueError, csv.Error) as error:
            warnings.warn(f"Skipping questionnaire {path.name}: {error}")
            continue
        matched = demographics.keys() & table.keys()
        if is_psq:
            columns = PSQ_COLUMNS
            observed = [sum(parse_score(table[pid][column]) is not None for column in columns) for pid in matched]
        else:
            observed = [sum(bool(value) for value in table[pid].values()) for pid in matched]
        inventory.append({
            "questionnaire": path.stem, "score_columns": len(columns), "source_rows": source_rows,
            "invalid_or_duplicate_id_rows": source_rows - len(table), "cohort_n": len(demographics),
            "matched_rows": len(matched), "unmatched_source_ids": len(table) - len(matched),
            "any_score_n": sum(count > 0 for count in observed),
            "complete_score_n": observed.count(len(columns)),
        })

    return inventory


def score_distribution(scores):
    counts = Counter(min(int(score // 10), 9) for score in scores)
    return [
        {"lower_inclusive": lower, "upper": lower + 10, "upper_inclusive": lower == 90, "n": counts[lower // 10]}
        for lower in range(0, 100, 10)
    ]


def main():
    demographics = read_demographics()
    psq_source = read_psq()
    _, psq, _ = psq_source
    groups = participant_groups(demographics)
    coverage = questionnaire_coverage(demographics, psq_source)
    descriptives = [
        describe(column, participants, psq, group)
        for column in PSQ_COLUMNS
        for group, participants in groups.items()
    ]
    total_scores = (parse_score(psq.get(pid, {}).get(OVERALL, "")) for pid in demographics)
    distribution = score_distribution(score for score in total_scores if score is not None)

    write_csv(OTHER_OUT / "questionnaire_coverage.csv", coverage)
    write_csv(OUT / "psq_descriptives.csv", descriptives)
    write_csv(OUT / "psq_overall_distribution.csv", distribution)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    copyfile(PSQ_FILE, PRIVATE / "PSQ.csv")
    print(f"{len(coverage)} questionnaire tables profiled for {len(demographics)} participants. Results: {OUT}")


if __name__ == "__main__":
    main()
