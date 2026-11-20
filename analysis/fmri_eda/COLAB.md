# Running the heavy fMRI step on Google Colab

[`colab/fmri_extract_colab.ipynb`](colab/fmri_extract_colab.ipynb) runs `scripts/eda_extract.py` on Colab, against scans stored in Google Drive. It does the slow part: reading every 2.2 GB scan once. Everything after that runs on a laptop in minutes.

**Used on 2026-11-20:**
- 150 scans processed from the shared Drive folder.
- One scan processed on both Colab and the laptop gave identical results (`results/verification_summary.csv`).

## Steps

1. **Drive.** Put the scans in one Drive folder; the notebook expects `MyDrive/ecqPSQdata`, which you can change in cell 1. Add to that folder:
   - `name_match.csv`, copied from `data/LEMON/`;
   - a `confounds/` subfolder, copied from `data/LEMON/MRI_extras/confounds/`.

   If these are missing, the scans are still processed; the confounds are then read on the laptop instead.
2. **Colab.** Upload the notebook with *File → Upload notebook*. Under *Runtime → Change runtime type*, pick the option with the most RAM. The GPU is not used: the work is unzipping and NumPy, about 7 GB of RAM per scan.
3. **Run the cells in order.**
   - Cell 2 mounts Drive; you click the permission popup.
   - Cell 3 chooses how many scans to process at once from the available RAM.
   - Cell 5 lists what was found.
   - Cell 7 runs. It took about 17 s per scan with several running at once.
   - Cell 8 checks the output and zips it.
4. **Resume.** People already in the output folder (`MyDrive/task3_eda_cache`) are skipped. After a disconnect, just run all cells again.
5. **Back on the laptop.**
   - Copy the output files into `data/derived/fmri_eda/eda/cache/`, which is not in Git.
   - Then run `eda_report.py` and `eda_verify.py --all`; the commands are in the [README](README.md).

## Notes

- **Keep the notebook in sync.** If `scripts/eda_extract.py` changes, regenerate the notebook with `uv run python analysis/fmri_eda/scripts/build_colab_notebook.py`. The notebook embeds the script, so there is only one version of the code.
- **Controlling Colab from Claude Code didn't work.** We tried the Colab MCP server (`.mcp.json`), but the connection times out after 30 s, so the notebook was run by hand.
- **Privacy.** Per-person outputs stay in Drive and in `data/derived/`, never in Git.
