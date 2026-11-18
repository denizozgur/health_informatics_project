"""Fetch two fixed inspection examples, not an analysis cohort."""

import json
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from fetch_lemon import BASE, DATA, SOURCE, listing, save


def main():
    inventory = pd.read_csv(SOURCE / "remote_inventory.csv")
    jobs = []
    # First ID in the 20–25 and 65–70 bins: selected without looking at images or scores.
    for participant in ("sub-010003", "sub-010002"):
        prefix = f"MRI_MPILMBB_LEMON/MRI_Raw/{participant}/ses-01/anat/"
        rows = inventory[inventory.relative_path.str.startswith(prefix)]
        for row in rows.itertuples():
            filename = Path(row.relative_path).name
            if filename.endswith(("_T1w.nii.gz", "_T2w.nii.gz", "_FLAIR.nii.gz", ".json")):
                jobs.append((row.url, DATA / "subset" / participant / filename))
        for extension in ("set", "fdt"):
            relative = f"EEG_MPILMBB_LEMON/EEG_Preprocessed_BIDS_ID/EEG_Preprocessed/{participant}_EO.{extension}"
            jobs.append((BASE + relative, DATA / "subset" / participant / Path(relative).name))
        _, children = listing(f"EEG_MPILMBB_LEMON/EEG_Raw_BIDS_ID/{participant}/RSEEG/")
        for child in children:
            if child["relative_path"].endswith((".vhdr", ".vmrk")):
                jobs.append((child["url"], DATA / "subset" / participant / Path(child["relative_path"]).name))
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(lambda job: save(*job), jobs))
    for participant in ("sub-010003", "sub-010002"):
        name = f"{participant}_ses-01_task-rest_acq-AP_run-01_bold.json"
        relative = f"MRI_MPILMBB_LEMON/MRI_Raw/{participant}/ses-01/func/{name}"
        records.append(save(BASE + relative, DATA / "subset" / participant / name))
    raw_url = BASE + "EEG_MPILMBB_LEMON/EEG_Raw_BIDS_ID/sub-010002/RSEEG/sub-010002.eeg"
    prefix_path = DATA / "subset/sub-010002/sub-010002_first10s.eeg"
    headers = SOURCE / "raw_eeg_range_headers.txt"
    if not prefix_path.exists():
        subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--max-time", "90",
                        "--range", "0-3099999", "--max-filesize", "3100000", "-D", str(headers),
                        raw_url, "-o", str(prefix_path)], check=True)
    if prefix_path.stat().st_size != 3100000 or "Content-Range: bytes 0-3099999/" not in headers.read_text():
        raise ValueError("Raw EEG range response did not match the requested 10 s prefix")
    records.append({"url": raw_url, "path": str(prefix_path.relative_to(DATA.parents[1])),
                    "bytes": prefix_path.stat().st_size, "byte_range": "0-3099999",
                    "sha256": hashlib.sha256(prefix_path.read_bytes()).hexdigest()})
    (SOURCE / "subset_manifest.json").write_text(json.dumps({
        "selection": "First lexicographic ID in each of the 20-25 and 65-70 age bins",
        "purpose": "Visual inspection only; not representative of population variation",
        "files": records}, indent=2))
    print(f"Downloaded {len(records)} files, {sum(r['bytes'] for r in records):,} bytes")


if __name__ == "__main__":
    main()
