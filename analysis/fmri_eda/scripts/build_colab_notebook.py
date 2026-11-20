#!/usr/bin/env python
"""Build analysis/fmri_eda/colab/fmri_extract_colab.ipynb from the current eda_extract.py.

    uv run python analysis/fmri_eda/scripts/build_colab_notebook.py

The notebook embeds eda_extract.py verbatim (via %%writefile), so there is one source of truth:
re-run this builder after changing eda_extract.py. The notebook only does the heavy step
(reading every scan); eda_report.py and eda_verify.py run on the laptop on the downloaded cache.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "colab" / "fmri_extract_colab.ipynb"
SRC = (HERE / "eda_extract.py").read_text()


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n")}


cells = [
    md("""
# fMRI EDA - heavy step on Colab

What this notebook does: reads every preprocessed LEMON resting-state scan (`*_MNI2mm.nii.gz`, ~2.2 GB each)
in a Google Drive folder **once**, and writes a small summary file per participant (`<id>.npz` + `<id>.json`,
~21 MB) to an output folder in Drive. This is `analysis/fmri_eda/scripts/eda_extract.py` from the repository,
embedded unchanged.

Afterwards, on the laptop: copy the output folder to `data/derived/fmri_eda/eda/cache/` and run
`eda_report.py` (checks, tables, figures) and `eda_verify.py` (independent re-check).

**Before running:** Runtime -> Change runtime type -> pick a runtime with lots of RAM (G4 / A100 / High-RAM).
The work is CPU and memory bound (decompressing gzip); the GPU itself is not used.

**Safe to re-run:** participants already in the output folder are skipped, so after a disconnect just run all cells again.
"""),
    md("## 1. Settings"),
    code("""
DATA_DIR  = "/content/drive/MyDrive/ecqPSQdata"        # folder with the *_MNI2mm.nii.gz scans (subfolders are searched too)
CONF_DIR  = DATA_DIR + "/confounds"                     # *_confounds.txt; falls back to DATA_DIR if this folder is missing
NAME_MATCH = DATA_DIR + "/name_match.csv"               # public ID (sub-0100xx) -> archive ID (sub-0323xx), needed for confounds
OUT_DIR   = "/content/drive/MyDrive/task3_eda_cache"    # results; kept OUTSIDE the shared data folder on purpose
WORKERS   = None                                        # None = choose automatically from RAM and CPUs
ONLY_IDS  = []                                          # e.g. ["sub-010005"] for a quick test run; [] = all
"""),
    md("## 2. Connect Google Drive (a permission popup appears)"),
    code("""
from google.colab import drive
drive.mount("/content/drive")
"""),
    md("## 3. Check the machine and choose how many scans to process at once\nEach scan needs about 7 GB of RAM while it is processed (measured)."),
    code("""
import os, subprocess
ram_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
cpus = os.cpu_count()
auto = max(1, min(cpus, int((ram_gb - 4) // 8)))
WORKERS = WORKERS or auto
print(f"RAM {ram_gb:.0f} GB, CPUs {cpus} -> {WORKERS} scan(s) at once")
print(subprocess.run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader", shell=True,
                     capture_output=True, text=True).stdout or "no GPU (not needed)")
"""),
    md("## 4. Install the two libraries (nibabel reads NIfTI; isal = faster gzip, identical output)"),
    code("!pip -q install nibabel isal"),
    md("## 5. Look at what is in the Drive folder before starting"),
    code("""
from pathlib import Path
scans = sorted(Path(DATA_DIR).rglob("sub-*_MNI2mm.nii.gz"))
if not Path(CONF_DIR).is_dir():
    CONF_DIR = DATA_DIR
confs = sorted(Path(CONF_DIR).glob("*_confounds.txt"))
done = sorted(Path(OUT_DIR).glob("sub-*.json")) if Path(OUT_DIR).exists() else []
print(f"scans found         : {len(scans)}  ({sum(p.stat().st_size for p in scans) / 1e9:.0f} GB)")
print(f"confounds files     : {len(confs)}  in {CONF_DIR}")
print(f"name_match.csv      : {'found' if Path(NAME_MATCH).exists() else 'MISSING -> confound checks will be skipped'}")
print(f"already done (skip) : {len(done)}")
small = [p.name for p in scans if p.stat().st_size < 1.5e9]
if small:
    print("WARNING, unusually small (incomplete upload?):", small)
assert scans, "No scans found: check DATA_DIR"
"""),
    md("## 6. The extraction script (copied from the repository - do not edit here)"),
    code("%%writefile /content/eda_extract.py\n" + SRC),
    md("## 7. Run\nProgress is printed per scan. Measured on a laptop: ~50 s per scan with one worker."),
    code("""
ids = " ".join(ONLY_IDS)
!cd /content && python eda_extract.py {ids} --mri-dir "{DATA_DIR}" --conf-dir "{CONF_DIR}" --name-match "{NAME_MATCH}" --cache-dir "{OUT_DIR}" --workers {WORKERS}
"""),
    md("## 8. Check the result and pack it for download"),
    code("""
import json, shutil
js = sorted(Path(OUT_DIR).glob("sub-*.json"))
npz = {p.stem for p in Path(OUT_DIR).glob("sub-*.npz")}
print(f"{len(js)} participants finished, {len([j for j in js if j.stem not in npz])} missing their .npz")
bad = [j.stem for j in js if json.loads(j.read_text())["shape"][3] != 652]
print("scans without 652 volumes:", bad or "none")
missing = sorted({p.name.split('_')[0] for p in scans} - {j.stem for j in js})
print("not finished (re-run cell 7):", missing or "none")
shutil.make_archive("/content/task3_eda_cache", "zip", OUT_DIR)
print("zip:", "/content/task3_eda_cache.zip", f"{Path('/content/task3_eda_cache.zip').stat().st_size / 1e9:.1f} GB")
"""),
    md("""
## 9. Back on the laptop

1. Download `task3_eda_cache` from Drive (or the zip from the Colab file panel).
2. Put its contents in `data/derived/fmri_eda/eda/cache/` (never in the Git-tracked `analysis/` folder).
3. Run:
```
uv run python analysis/fmri_eda/scripts/eda_report.py
uv run python analysis/fmri_eda/scripts/eda_verify.py --all
```
"""),
]

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                                   "kernelspec": {"display_name": "Python 3", "name": "python3"},
                                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
for c in nb["cells"]:   # notebooks store source as a list of lines
    c["source"] = c["source"].splitlines(keepends=True)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(nb, indent=1))
print("wrote", OUT)
