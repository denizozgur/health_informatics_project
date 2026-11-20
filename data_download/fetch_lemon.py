"""Download small LEMON tables and record remote listings without bulk imaging."""

import argparse
import csv
import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urljoin

BASE = "https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/lemon"
SOURCE = DATA / "source"


def get(url):
    return subprocess.check_output(
        ["curl", "--fail", "--location", "--silent", "--show-error",
         "--retry", "2", "--max-time", "90", url]
    )


def save(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        payload = get(url)
        temporary = path.with_name(path.name + ".partial")
        temporary.write_bytes(payload)
        temporary.replace(path)
    payload = path.read_bytes()
    return {"url": url, "path": str(path.relative_to(ROOT)), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


def listing(relative):
    url = BASE + quote(relative, safe="/")
    path = SOURCE / "listings" / (relative.rstrip("/") or "root") / "index.html"
    record = save(url, path)
    html = path.read_text()
    links = re.findall(r'<a href="([^"]+)">', html)
    entries = []
    for link in links:
        if link.startswith(("../", "?", "/")):
            continue
        name = unquote(link)
        line = next((line for line in html.splitlines() if f'href="{link}"' in line), "")
        size = re.search(r"\s(\d+)\s*$", line)
        entries.append({"relative_path": relative + name, "directory": name.endswith("/"),
                        "url": urljoin(url, link), "listed_bytes": int(size[1]) if size else None})
    return record, entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-mri", action="store_true",
                        help="List every raw MRI directory, without downloading image payloads")
    parser.add_argument("--inventory-all", action="store_true",
                        help="Recursively list the entire GWDG archive; no extra data payloads")
    args = parser.parse_args()
    SOURCE.mkdir(parents=True, exist_ok=True)
    manifest, entries, errors = [], [], []
    frontier = ["Behavioural_Data_MPILMBB_LEMON/"]
    with ThreadPoolExecutor(max_workers=8) as executor:
        while frontier:
            results = list(executor.map(listing, frontier))
            frontier = []
            for record, children in results:
                manifest.append(record)
                entries.extend(children)
                for child in children:
                    if child["directory"]:
                        frontier.append(child["relative_path"])
                    else:
                        manifest.append(save(child["url"], SOURCE / child["relative_path"]))
    roots = ["MRI_MPILMBB_LEMON/", "MRI_MPILMBB_LEMON/MRI_Raw/",
             "MRI_MPILMBB_LEMON/MRI_Preprocessed_Derivetives/",
             "EEG_MPILMBB_LEMON/", "EEG_MPILMBB_LEMON/EEG_Raw_BIDS_ID/",
             "EEG_MPILMBB_LEMON/EEG_Preprocessed_BIDS_ID/",
             "EEG_MPILMBB_LEMON/EEG_Preprocessed_BIDS_ID/EEG_Preprocessed/",
             "EEG_MPILMBB_LEMON/EEG_Localizer_BIDS_ID/"]
    for relative in roots:
        record, children = listing(relative)
        manifest.append(record)
        entries.extend(children)
        if relative in ("MRI_MPILMBB_LEMON/", "EEG_MPILMBB_LEMON/"):
            for child in children:
                if not child["directory"]:
                    manifest.append(save(child["url"], SOURCE / child["relative_path"]))
    if args.inventory_mri or args.inventory_all:
        frontier = [e["relative_path"] for e in entries
                    if e["directory"] and re.fullmatch(r"MRI_MPILMBB_LEMON/MRI_Raw/sub-\d+/", e["relative_path"])]
        with ThreadPoolExecutor(max_workers=12) as executor:
            while frontier:
                following = []
                for relative, future in zip(frontier, [executor.submit(listing, r) for r in frontier]):
                    try:
                        record, children = future.result()
                    except Exception as exc:
                        errors.append({"directory": relative, "error": str(exc)})
                        continue
                    manifest.append(record)
                    entries.extend(children)
                    following.extend(c["relative_path"] for c in children if c["directory"])
                print(f"Listed {len(frontier)} MRI directories; next level {len(following)}", flush=True)
                frontier = following
    if args.inventory_all:
        frontier, seen = [""], set()
        with ThreadPoolExecutor(max_workers=12) as executor:
            while frontier:
                following = []
                if len(seen) + len(frontier) > 10000:
                    raise RuntimeError("Directory inventory exceeded 10,000-directory safety limit")
                for relative, future in zip(frontier, [executor.submit(listing, r) for r in frontier]):
                    seen.add(relative)
                    try:
                        record, children = future.result()
                    except Exception as exc:
                        errors.append({"directory": relative, "error": str(exc)})
                        continue
                    manifest.append(record)
                    entries.extend(children)
                    following.extend(c["relative_path"] for c in children
                                     if c["directory"] and c["relative_path"] not in seen)
                print(f"Archive inventory: {len(seen)} directories listed; next level {len(following)}", flush=True)
                frontier = list(dict.fromkeys(following))
    unique = {e["relative_path"]: e for e in entries}
    with (SOURCE / "remote_inventory.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=["relative_path", "directory", "url", "listed_bytes"])
        writer.writeheader()
        writer.writerows(sorted(unique.values(), key=lambda x: x["relative_path"]))
    (SOURCE / "fetch_manifest.json").write_text(json.dumps({
        "retrieved_utc": datetime.now(timezone.utc).isoformat(), "base_url": BASE,
        "raw_mri_recursively_listed": args.inventory_mri or args.inventory_all,
        "entire_archive_recursively_listed": args.inventory_all, "errors": errors,
        "files": list({r['path']: r for r in manifest}.values())}, indent=2))
    print(f"Saved {len(manifest)} source files/listings; {len(unique)} remote entries; {len(errors)} errors")


if __name__ == "__main__":
    main()
