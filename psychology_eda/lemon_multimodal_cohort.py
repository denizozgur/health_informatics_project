"""List participants with PSQ, resting-state fMRI and resting-state EEG."""

import csv
import re
from collections import defaultdict
from dataclasses import dataclass

from .lemon_psychology_eda import INVENTORY, OVERALL, ROOT, read_psq_totals, write_csv

OUT = ROOT / "outputs/lemon/multimodal"
BOLD = re.compile(
    r"(?:MRI_MPILMBB_LEMON/)?MRI_Raw/(sub-\d{6})/(ses-[^/]+)/func/"
    r"\1_\2_task-rest(?:_[^/]+)?_bold\.nii(?:\.gz)?"
)
RAW_EEG = re.compile(
    r"EEG_MPILMBB_LEMON/EEG_Raw_BIDS_ID/(sub-\d{6})/RSEEG/\1\.(eeg|vhdr|vmrk)"
)
PROCESSED_EEG = re.compile(
    r"EEG_MPILMBB_LEMON/EEG_Preprocessed_BIDS_ID/EEG_Preprocessed/"
    r"(sub-\d{6})_(EO|EC)\.(set|fdt)"
)


@dataclass
class ArchiveFiles:
    """File paths grouped by the participant ID in the archive."""

    bold: dict[str, set[str]]
    raw_eeg: dict[str, dict[str, str]]
    processed_eeg: dict[tuple[str, str], dict[str, str]]
    unverified: dict[str, set[str]]

    def eeg_ids(self):
        processed_ids = {participant_id for participant_id, _ in self.processed_eeg}
        return self.raw_eeg.keys() | processed_ids

    def eeg_file_sets(self, participant_id):
        """Return complete EEG alternatives in raw, eyes-open, eyes-closed order."""
        options = (
            self.raw_eeg.get(participant_id),
            self.processed_eeg.get((participant_id, "EO")),
            self.processed_eeg.get((participant_id, "EC")),
        )
        return [tuple(files.values()) for files in options if files]

    def participant_ids(self):
        return self.bold.keys() | self.eeg_ids() | self.unverified.keys()


def scan_inventory(inventory_path):
    bold = defaultdict(set)
    raw_eeg = defaultdict(dict)
    processed_eeg = defaultdict(dict)
    unverified_files = defaultdict(set)
    with inventory_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"relative_path", "directory", "listed_bytes"} <= set(reader.fieldnames or []):
            raise ValueError(f"{inventory_path}: expected relative_path, directory and listed_bytes")
        for row in reader:
            if (row["directory"] or "").strip().casefold() not in {"false", "0"}:
                continue
            path = (row["relative_path"] or "").strip().lstrip("/")
            bold_match = BOLD.fullmatch(path)
            raw_match = RAW_EEG.fullmatch(path)
            processed_match = PROCESSED_EEG.fullmatch(path)
            match = bold_match or raw_match or processed_match
            if match is None:
                continue
            size = (row["listed_bytes"] or "").strip()
            if not size.isdecimal() or int(size) == 0:
                unverified_files[match[1]].add(path)
            elif bold_match:
                bold[match[1]].add(path)
            elif raw_match:
                raw_eeg[match[1]][match[2]] = path
            else:
                processed_eeg[match[1], match[2]][match[3]] = path

    raw_eeg = {pid: files for pid, files in raw_eeg.items() if files.keys() == {"eeg", "vhdr", "vmrk"}}
    processed_eeg = {
        key: files for key, files in processed_eeg.items() if files.keys() == {"set", "fdt"}
    }
    if not bold or not (raw_eeg or processed_eeg):
        raise ValueError(f"{inventory_path}: missing resting-state fMRI or complete EEG listings")
    return ArchiveFiles(bold, raw_eeg, processed_eeg, unverified_files)


def evidence_row(pid, score, files, included):
    raw = files.raw_eeg.get(pid, {})
    eyes_open = files.processed_eeg.get((pid, "EO"), {})
    eyes_closed = files.processed_eeg.get((pid, "EC"), {})
    bold_paths = sorted(files.bold.get(pid, ()))
    return {
        "ID": pid,
        OVERALL: score,
        "included": included,
        "rest_bold_count": len(bold_paths),
        "rest_bold_path": bold_paths[0] if bold_paths else "",
        "raw_eeg_path": raw.get("eeg", ""),
        "raw_vhdr_path": raw.get("vhdr", ""),
        "raw_vmrk_path": raw.get("vmrk", ""),
        "eo_set_path": eyes_open.get("set", ""),
        "eo_fdt_path": eyes_open.get("fdt", ""),
        "ec_set_path": eyes_closed.get("set", ""),
        "ec_fdt_path": eyes_closed.get("fdt", ""),
        "empty_or_unknown_size_paths": " | ".join(sorted(files.unverified.get(pid, ()))),
    }


def main():
    scores = read_psq_totals()
    files = scan_inventory(INVENTORY)
    psq_ids = {pid for pid, score in scores.items() if score is not None}
    fmri_ids = files.bold.keys()
    eeg_ids = files.eeg_ids()
    matched = psq_ids & fmri_ids & eeg_ids

    path = OUT / "psq_fmri_eeg_subjects.csv"
    write_csv(path, [{"ID": pid} for pid in sorted(matched)], fieldnames=["ID"])
    write_csv(OUT / "psq_fmri_eeg_evidence.csv", [
        evidence_row(pid, scores.get(pid), files, included=pid in matched)
        for pid in sorted(scores.keys() | files.participant_ids())
    ])
    print(f"Valid PSQ: {len(psq_ids)} | Resting fMRI: {len(fmri_ids)} | Resting EEG: {len(eeg_ids)}")
    print(f"All three: {len(matched)}. Archive availability: {path}")


if __name__ == "__main__":
    main()
