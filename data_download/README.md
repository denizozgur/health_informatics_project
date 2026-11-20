# Data download

These are a teammate's scripts for mirroring the public [LEMON archive](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/) into `data/lemon/`, which is not in Git.

| Script | What it downloads |
|---|---|
| `fetch_lemon.py` | The archive listings and all small files: behavioural tables, info files and sidecars. It writes `data/lemon/source/remote_inventory.csv`, a list of every file in the archive |
| `fetch_lemon_subset.py` | Raw files for a few participants (MRI, EEG, physiology) into `data/lemon/subset/`, chosen from the inventory |
| `fetch_lemon_papers.py` | The LEMON papers and their supplements, from Europe PMC |

Run them from the project root, in this order:

```bash
uv run python data_download/fetch_lemon.py
```

```bash
uv run python data_download/fetch_lemon_subset.py
```

```bash
uv run python data_download/fetch_lemon_papers.py
```

**Check disk space and what you need before downloading.** The full archive is hundreds of GB.

**Two data folders.** The analyses in `participant_table`, `stress_questionnaires` and `fmri_eda` were written against a manual download in `data/LEMON/`. The teammate's scripts use the mirror in `data/lemon/source/`. Both hold the same LEMON files in different folder layouts. On macOS, which ignores upper/lower case in folder names, the two paths are the same folder. They should be merged into one layout.
