"""Inspect one LEMON rest run before computing HRV or fMRI features."""

import argparse
import csv
import gzip
import json
import math
from pathlib import Path

import nibabel as nib
import numpy as np


def check_psq(path: Path, subject: str) -> bool:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        values = [row["PSQ_OverallScore"] for row in csv.DictReader(stream) if row["ID"] == subject]
    if len(values) != 1:
        return False
    try:
        score = float(values[0])
    except ValueError:
        return False
    return 0 <= score <= 100


def inspect_physio(stem: Path, channel: str) -> tuple[dict, np.ndarray]:
    metadata = json.loads(stem.with_suffix(".json").read_text())
    columns = metadata["Columns"]
    sampling_hz = float(metadata["SamplingFrequency"])
    start_s = float(metadata["StartTime"])
    if not math.isfinite(sampling_hz) or sampling_hz <= 0 or not math.isfinite(start_s):
        raise ValueError(f"Invalid timing metadata in {stem}")

    samples = np.loadtxt(stem.with_suffix(".tsv.gz"), ndmin=2)
    if samples.shape[1] != len(columns) or not np.isfinite(samples).all():
        raise ValueError(f"Invalid physiological samples in {stem}")

    signal = samples[:, columns.index(channel)]
    trigger = samples[:, columns.index("trigger")]
    if not np.isin(trigger, [0, 1]).all():
        raise ValueError(f"Expected a binary trigger in {stem}")
    high = trigger == 1
    edges = np.flatnonzero(high & ~np.r_[False, high[:-1]])
    trigger_times = start_s + edges / sampling_hz

    return {
        "sampling_hz": sampling_hz,
        "start_s": start_s,
        "end_s_exclusive": round(start_s + len(samples) / sampling_hz, 6),
        "samples": len(samples),
        "triggers": len(edges),
        "median_trigger_interval_s": round(float(np.median(np.diff(trigger_times))), 6)
        if len(edges) > 1 else None,
        "signal_p01_p50_p99": np.percentile(signal, [1, 50, 99]).round(4).tolist(),
    }, trigger_times


def inspect_run(directory: Path, subject: str) -> dict:
    prefix = f"{subject}_ses-01_task-rest_acq-AP_run-01"
    raw_metadata = json.loads((directory / f"{prefix}_bold.json").read_text())
    acquisition_tr = float(raw_metadata["RepetitionTime"])
    if not math.isfinite(acquisition_tr) or acquisition_tr <= 0:
        raise ValueError("Invalid acquisition TR")

    fmri = directory / f"{prefix}_MNI2mm.nii.gz"
    header_only = not fmri.is_file()
    if header_only:
        with gzip.open(directory / f"{prefix}_MNI2mm.header.gz", "rb") as stream:
            header = nib.Nifti1Header.from_fileobj(stream)
    else:
        header = nib.load(fmri).header

    shape = header.get_data_shape()
    if len(shape) != 4:
        raise ValueError(f"Expected a 4-D BOLD scan, got {shape}")
    header_tr = float(header.get_zooms()[3])
    ecg, ecg_times = inspect_physio(directory / f"{prefix}_recording-ecg_physio", "ecg")
    resp, resp_times = inspect_physio(directory / f"{prefix}_recording-resp_physio", "resp")

    # LEMON documentation describes discarding five initial fMRI volumes.
    dropped = 5
    expected_triggers = shape[3] + dropped
    expected_times = np.arange(expected_triggers) * acquisition_tr
    expected_end = expected_triggers * acquisition_tr
    ecg_grid_matches = len(ecg_times) == expected_triggers and bool(
        np.allclose(ecg_times, expected_times, rtol=0, atol=0.001)
    )
    resp_prefix_matches = len(resp_times) >= expected_triggers and bool(
        np.allclose(resp_times[:expected_triggers], expected_times, rtol=0, atol=0.001)
    )
    candidate_window = None
    if (ecg_grid_matches and resp_prefix_matches
            and min(ecg["end_s_exclusive"], resp["end_s_exclusive"]) + 0.001 >= expected_end):
        candidate_window = [
            round(float(expected_times[dropped]), 6),
            round(float(expected_end), 6),
        ]

    return {
        "subject": subject,
        "run": prefix,
        "fmri": {
            "shape": list(shape),
            "voxel_size_mm": [float(value) for value in header.get_zooms()[:3]],
            "header_tr": header_tr,
            "header_time_unit": header.get_xyzt_units()[1],
            "raw_sidecar_tr_s": acquisition_tr,
            "header_agrees_with_sidecar": header.get_xyzt_units()[1] == "sec"
            and math.isclose(header_tr, acquisition_tr, abs_tol=1e-5),
            "header_only_available": header_only,
        },
        "ecg": ecg,
        "resp": resp,
        "alignment": {
            "expected_raw_triggers": expected_triggers,
            "ecg_grid_matches": ecg_grid_matches,
            "resp_prefix_matches": resp_prefix_matches,
            "resp_extra_triggers": max(len(resp_times) - expected_triggers, 0),
            "provisional_window_s_end_exclusive": candidate_window,
            "status": "requires_review",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject", help="Subject ID, e.g. sub-010005")
    parser.add_argument("--directory", type=Path, help="Directory containing files for this run")
    parser.add_argument("--psq-csv", type=Path, default=Path("data/LEMON/Emotion_and_Personality_Test_Battery_LEMON/PSQ.csv"))
    args = parser.parse_args()
    directory = args.directory or Path("data/lemon/pilot") / args.subject
    report = inspect_run(directory, args.subject)
    report["valid_psq"] = check_psq(args.psq_csv, args.subject)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
