# Health informatics project

A small Python 3.12 environment for Jupyter notebooks and exploration of the [OpenNeuro ds005892 resting-state MRI dataset](https://github.com/OpenNeuroDatasets/ds005892). The dataset is stored locally in `ds005892/` and is excluded from this project's Git repository.

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

## Download the dataset

The dataset is excluded from this project's Git repository, so it must be downloaded separately on each machine. As of November 2026, the public dataset is approximately 2.21 GiB; allow extra disk space for your work. The following downloads the actual files directly from OpenNeuro's public S3 bucket; an AWS account is not needed.

1. Install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) separately from the Python project and confirm `aws --version` works.
2. From the project root, download into a **new or existing data directory**:

   ```bash
   aws s3 sync --no-sign-request s3://openneuro.org/ds005892/ ds005892/
   ```

   The command can be run again after an interrupted download. It can update existing files in `ds005892/`, so review any local edits before running it. It does not delete local files unless `--delete` is supplied.
3. Check that a scan can be opened using the project environment:

   ```bash
   uv run --locked python -c "import nibabel as nib; img = nib.load('ds005892/sub-MJF001/anat/sub-MJF001_T1w.nii.gz'); print('Image shape:', img.shape)"
   ```

   This checks one scan; it does not verify every file. For download and version options, see the [OpenNeuro dataset page](https://openneuro.org/datasets/ds005892) and its dataset README.

A plain clone of the [dataset's Git repository](https://github.com/OpenNeuroDatasets/ds005892) contains git-annex links for large files, rather than the scan contents. The S3 method above downloads the contents directly and does not require a Git clone or git-annex. The dataset is shared under CC0; follow its README for attribution and study details.
