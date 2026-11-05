# Health informatics project

A small Python 3.12 environment for Jupyter notebooks and exploration of the [OpenNeuro ds005892 resting-state MRI dataset](https://github.com/OpenNeuroDatasets/ds005892). The dataset is stored locally in `ds005892/` and is excluded from this project's Git repository.

## Set up the environment

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12, then from the project directory run:

```bash
uv sync --locked
```

This creates `.venv` and installs the versions recorded in `uv.lock`. Start JupyterLab with:

```bash
uv run --locked jupyter lab
```

Open or create an `.ipynb` notebook and select the project's Python kernel. Alternatively activate the environment with `source .venv/bin/activate`; leave it with `deactivate`.

The direct dependencies are JupyterLab, NumPy, pandas, SciPy, Matplotlib, and NiBabel (for MRI/NIfTI files). The environment and dataset are not committed. See `AGENTS.md` for safely adding dependencies.

## Dataset

The dataset is provided by OpenNeuro under CC0; refer to its README for attribution and study details. A plain Git clone contains git-annex links rather than the MRI file contents: use DataLad/git-annex or OpenNeuro's download options to retrieve the actual data on another machine. This local copy contains the files downloaded from OpenNeuro's public S3 bucket.
