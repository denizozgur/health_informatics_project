# LEMON ECG EDA

Open [ECG_EDA.ipynb](ECG_EDA.ipynb) in the project’s Python 3.12 environment and run all cells to view the 206-participant summary and five figures. The published results are in [results/](results/).

For a new analysis, install the project’s ECG extra with `uv sync --locked --extra ecg`. In the notebook, set `DATA_DIR` to the folder containing the ECG TSV files and matching JSON sidecars, then set `RUN_ANALYSIS = True`. New results go to `outputs/lemon/ecg_notebook/`.

The portable analysis produces recording metrics, candidate beat detections, and exploratory review flags. Participant-level outputs are stored under `private/`. The original demographic figures are bundled snapshots, and a new run produces a recording-duration and amplitude-variability overview. Validated HRV requires separate beat review.
