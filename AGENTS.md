# Project instructions

- Use Python 3.12 and the project-managed `.venv` with `uv`.
- Keep `data/`, `.venv/`, notebook checkpoints, and Python caches out of Git. Do not commit participant data, generated datasets, or large outputs.
- Add only dependencies needed for the task. From the project root, use `uv add PACKAGE` rather than `pip install` or editing the environment directly. This updates `pyproject.toml` and `uv.lock` together. Use `uv add --dev PACKAGE` for development-only tools.
- Preserve the existing lockfile and dependencies where possible. Review the lockfile diff for unintended upgrades; `uv add` can change transitive dependencies if necessary, and compatibility is not guaranteed merely by successful resolution. Avoid `uv lock --upgrade` unless requested.
- Run `uv sync --locked` and relevant import or notebook checks after changes. Check `uv run --locked python -m pip` only if pip is deliberately installed; it is not required for this project. Commit both dependency files when they change. If resolution fails, explain the conflict instead of forcing incompatible versions.
