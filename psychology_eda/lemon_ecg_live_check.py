"""Verify first-byte access for same-scan LEMON fMRI and ECG candidates."""

import csv
from concurrent.futures import ThreadPoolExecutor
from urllib.error import URLError
from urllib.request import urlopen

from .lemon_cohort_eda import RUN
from .lemon_live_check import ARCHIVE, check_file_sets
from .lemon_multimodal_cohort import OUT
from .lemon_psychology_eda import OTHER_OUT, read_psq_totals, write_csv

CANDIDATES = OTHER_OUT / "psq_bold_ecg_candidates.csv"


def read_candidates(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        candidates = list(csv.DictReader(stream))
    if not candidates:
        raise ValueError(f"No ECG candidates in {path}")
    if len(candidates) != len({row["ID"] for row in candidates}):
        raise ValueError(f"Duplicate participant IDs in {path}")

    for row in candidates:
        for field, suffix in (("bold_path", "_bold.nii.gz"), ("ecg_path", "_recording-ecg_physio.tsv.gz")):
            match = RUN.search(row[field] or "")
            if match is None or match[1] != row["ID"] or match["suffix"] != suffix:
                raise ValueError(f"{row['ID']}: unexpected scan in {field}")
    return candidates


def check_subject(row, valid_psq):
    fmri = ecg = "not_checked"
    bold_error = ecg_error = ""
    if valid_psq:
        fmri, _, bold_error = check_file_sets([(row["bold_path"],)] if row["bold_path"] else [])
        ecg, _, ecg_error = check_file_sets([(row["ecg_path"],)] if row["ecg_path"] else [])

    return {
        "ID": row["ID"],
        "valid_psq": valid_psq,
        "fmri": fmri,
        "ecg": ecg,
        "verified_all_three": valid_psq and fmri == "verified" and ecg == "verified",
        "bold_path": row["bold_path"],
        "ecg_path": row["ecg_path"],
        "errors": " | ".join(filter(None, (bold_error, ecg_error))),
    }


def main():
    candidates = read_candidates(CANDIDATES)
    scores = read_psq_totals()

    try:
        with urlopen(ARCHIVE, timeout=15):
            pass
    except (URLError, OSError) as error:
        raise SystemExit(f"Cannot reach LEMON archive: {error}. Verification did not run.") from error

    def verify(row):
        return check_subject(row, scores.get(row["ID"]) is not None)

    print(f"Checking {len(candidates)} PSQ, fMRI and ECG candidates.", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index, result in enumerate(pool.map(verify, candidates), start=1):
            results.append(result)
            if index % 25 == 0 or index == len(candidates):
                print(f"Checked {index}/{len(candidates)}", flush=True)

    verified = [{"ID": row["ID"]} for row in results if row["verified_all_three"]]
    write_csv(OUT / "psq_fmri_ecg_live_check.csv", results)
    write_csv(OUT / "psq_fmri_ecg_live_verified_subjects.csv", verified, fieldnames=["ID"])
    print(f"Verified all three: {len(verified)}/{len(candidates)}")


if __name__ == "__main__":
    main()
