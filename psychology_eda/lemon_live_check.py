"""Confirm one-byte access to the files behind the LEMON cohort."""

import re
import socket
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .lemon_multimodal_cohort import OUT, scan_inventory
from .lemon_psychology_eda import INVENTORY, read_psq_totals, write_csv

HOST = "ftp.gwdg.de"
ARCHIVE = f"https://{HOST}/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/"
CONTENT_RANGE = re.compile(r"bytes 0-0/[1-9]\d*")


def check_first_byte(path):
    request = Request(ARCHIVE + quote(path), headers={"Range": "bytes=0-0", "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=12) as response:
            content_range = response.headers.get("Content-Range", "")
            length = response.headers.get("Content-Length")
            if response.status != 206 or not CONTENT_RANGE.fullmatch(content_range) or length not in (None, "1"):
                return f"invalid range response (HTTP {response.status})"
            if len(response.read(1)) != 1:
                return "empty range response"
    except HTTPError as error:
        error.close()
        return f"HTTP {error.code}"
    except (URLError, OSError, HTTPException) as error:
        return str(error)
    return None


def check_file_sets(options):
    """Pass when every file in at least one complete option serves one byte."""
    if not options:
        return "not_listed", (), ""

    errors = []
    for paths in options:
        for path in paths:
            problem = check_first_byte(path)
            if problem is not None:
                errors.append(f"{path}: {problem}")
                break
        else:
            return "verified", paths, ""

    return "unverified", (), " | ".join(errors)


def check_subject(pid, score, bold_paths, eeg_options):
    valid_psq = score is not None
    fmri = eeg = "not_checked"
    bold = eeg_paths = ()
    bold_errors = eeg_errors = ""
    if valid_psq:
        fmri, bold, bold_errors = check_file_sets([(path,) for path in sorted(bold_paths)])
        eeg, eeg_paths, eeg_errors = check_file_sets(eeg_options)

    return {
        "ID": pid,
        "valid_psq": valid_psq,
        "fmri": fmri,
        "eeg": eeg,
        "verified_all_three": valid_psq and fmri == "verified" and eeg == "verified",
        "verified_bold_path": bold[0] if bold else "",
        "verified_eeg_paths": " | ".join(eeg_paths),
        "errors": " | ".join(filter(None, (bold_errors, eeg_errors))),
    }


def main():
    scores = read_psq_totals()
    files = scan_inventory(INVENTORY)
    ids = sorted(scores.keys() | files.participant_ids())

    try:
        socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise SystemExit(f"Cannot resolve {HOST}: {error}. Live checks did not run.") from error

    def verify(pid):
        return check_subject(pid, scores.get(pid), files.bold.get(pid, ()), files.eeg_file_sets(pid))

    print(f"Checking {len(ids)} participant IDs. Only one byte per file is requested.", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, row in enumerate(pool.map(verify, ids), start=1):
            results.append(row)
            if index % 25 == 0 or index == len(ids):
                print(f"Checked {index}/{len(ids)} IDs", flush=True)

    summary_path = OUT / "psq_fmri_eeg_live_check.csv"
    verified_path = OUT / "psq_fmri_eeg_live_verified_subjects.csv"
    verified = [{"ID": row["ID"]} for row in results if row["verified_all_three"]]
    write_csv(summary_path, results)
    write_csv(verified_path, verified, fieldnames=["ID"])
    print(f"Verified all three: {len(verified)}")
    print(summary_path)
    print(verified_path)


if __name__ == "__main__":
    main()
