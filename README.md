# Health informatics project

A small Python 3.12 environment for VS Code notebooks and exploration of the [LEMON mind-brain-body dataset](https://www.nature.com/articles/sdata2018308). Local datasets are excluded from Git.

## Set up the environment

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12, then from the project directory run:

```bash
uv sync --locked
```

This creates `.venv` and installs the versions recorded in `uv.lock`.

## Run notebooks in VS Code

1. Install the Microsoft Python and Jupyter extensions in VS Code.
2. Open this project folder in VS Code and open or create an `.ipynb` file.
3. Choose **Select Kernel** at the top of the notebook, then select **Python Environments** and the project's `.venv` (Python 3.12). If it is not listed, use **Enter interpreter path** and select `.venv/bin/python`.
4. Run a cell using its run button or Shift+Enter. The environment includes `ipykernel`, so a separate JupyterLab server is unnecessary.

For terminal work, you can activate the environment with `source .venv/bin/activate`; leave it with `deactivate`.

The direct dependencies are ipykernel, NumPy, pandas, SciPy, Matplotlib, and NiBabel (for MRI/NIfTI files). The environment and dataset are not committed. See `AGENTS.md` for safely adding dependencies.

## LEMON dataset

LEMON combines MRI, EEG, behavioral measures, and peripheral physiology. Our first priority is the behavioral data: cognitive measures, questionnaires, demographics, and availability tables. EEG is the leading candidate for the first brain modality; resting-state fMRI is a later candidate that requires more preprocessing. Choose a target and determine modality overlap before modelling; do not assume every participant has every measurement. The original study describes 227 participants in younger and older groups: [Babayan et al. (2019)](https://doi.org/10.1038/sdata.2018.308).

The [original public archive](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/) separates behavioral, MRI, EEG, and physiology files. It is large: check available disk space and select the modalities and participants needed before downloading. A different, repackaged [NEMAR EEG release](https://www.nemar.org/dataset/nm000179) lists a 66.7 GB ZIP and 127 GB dataset size; those figures are not an estimate of the complete original archive. Check the applicable release's license and citation requirements.

On this machine the behavioral collection has been downloaded directly into `data/LEMON/`. It includes cognitive-test directories, questionnaires, demographics, and availability tables; their scores and participant overlap still need investigation. To download it on a Linux system with `wget`, from the project root run:

```bash
mkdir -p data/LEMON
wget -r -nc -np -nH --cut-dirs=4 -R 'index.html*' -P data/LEMON 'https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/Behavioural_Data_MPILMBB_LEMON/'
```

This retrieves the behavioral subtree, including availability tables; `-nc` skips existing files, so if a previous download was interrupted mid-file, remove that incomplete file before rerunning. Check wget's exit status and output for errors. Review the accompanying `*_info` files before interpreting variables. Record the retrieval date and release details, and retain originals unchanged.

Browse [MRI](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/MRI_MPILMBB_LEMON/), [EEG](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/EEG_MPILMBB_LEMON/), and [physiology](https://ftp.gwdg.de/pub/misc/MPI-Leipzig_Mind-Brain-Body-LEMON/Continuous_Peripheral_Physiology_During_MRI_MPI-LMBB/) before choosing and downloading subsets.
