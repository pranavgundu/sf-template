# Science Fair Template

A configurable Python starter for science fairs and independent research.

## Quick start

Run the interactive setup with [uv](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uvx --from git+https://github.com/pranavgundu/sf-template sf-template
```

From a local checkout, use `uvx --from . sf-template`.

Setup asks for the project name, folder, research type, ML framework if applicable, and optional packages. Press Enter to accept defaults.

## Packages by research type

Your choices determine the dependencies written to `pyproject.toml`.

| Research type | Default packages |
| --- | --- |
| Science | NumPy, SciPy, Matplotlib |
| Data analytics | NumPy, SciPy, Matplotlib, Pandas, Seaborn, Statsmodels, Openpyxl |
| ML | Scientific and data tools plus scikit-learn, PyTorch/Lightning, or JAX/Flax/Optax |
| Computer vision | Scientific and data tools, PyTorch, Lightning, Torchvision, Pillow |
| NLP | Scientific and data tools, PyTorch, Lightning, Transformers, Datasets, Evaluate |
| Computational | NumPy, SciPy, Matplotlib, SymPy, NetworkX |
| Literature review | Pandas, Bibtexparser |
| General | NumPy, SciPy, Matplotlib, Pandas, Seaborn |

Optional `--add` sets: `notebooks` (JupyterLab and IPykernel), `tracking` (W&B), and `config` (Hydra). These add packages; configure them in your own code as needed.

## Setup options

Start the prompts with a folder already chosen:

```sh
uvx --from . sf-template init ../my-research
```

Or supply your choices directly:

```sh
uvx --from . sf-template init ../ml-study --title "ML study" --starter ml --framework torch --add notebooks --add tracking
uvx --from . sf-template init ../analytics --title "Data study" --starter data-analytics
uvx --from . sf-template starters
```

Supply folder, title, and starter to skip prompts, or use `--no-input` for defaults.

## Run your project

```sh
cd ../my-research
uv sync
uv run python -m project.main
uv run python -m unittest discover -s tests
```

Edit `configs/experiment.toml` to select inputs and analysis settings. The default run summarizes synthetic data; literature review runs a source inventory. ML training is not implemented in the bundled example.

`uv sync` installs the selected packages and creates `uv.lock`. Commit the lockfile for reproducible environments. Python defaults to 3.12. GPU-specific wheels are not configured automatically.

## Project layout

```text
project/       Python code, with algorithms/, datasets/, and models/
configs/       Experiment settings
tests/         Calculation and configuration checks
data/          Raw, processed, and synthetic example data
results/       Separate outputs for each run
notebooks/     Your own notebooks
papers/        PDFs and manuscripts
notes/         Your own notes
general/       Other project materials
references/    Source list
```

## Development

```sh
uv run python -m unittest discover -s tests -v
uv build
```

[MIT license](LICENSE). The generator has no runtime dependencies and is not published to PyPI.
