Science Fair Template

Create a project (requires uv):
  uvx --from . sf-template

Setup asks for the project name, folder, research type, ML framework if
applicable, and optional package sets. Enter accepts the displayed defaults.
The menu shows each research type's default packages. Your choices determine
the dependencies written to pyproject.toml:
  Science: numpy, scipy, matplotlib
  Analytics: numpy, scipy, matplotlib, pandas, seaborn, statsmodels, openpyxl
  ML: scientific/data tools plus only the framework you select
  Computational: numpy, scipy, matplotlib, sympy, networkx
  Literature review: pandas, bibtexparser
  General: numpy, scipy, matplotlib, pandas, seaborn

You can also start the prompts with a folder already chosen:
  uvx --from . sf-template init ../my-research

Choose packages at creation:
  uvx --from . sf-template init ../ml-study --title "ML study" --starter ml --framework torch --add notebooks --add tracking
  uvx --from . sf-template init ../analytics --title "Data study" --starter data-analytics
  uvx --from . sf-template init ../vision --title "Image study" --starter computer-vision

Supply folder, title, and starter to skip prompts, or use --no-input for defaults.

ML supports sklearn (default), torch + lightning, or jax + flax + optax.
Computer vision uses torch, torchvision, and pillow. NLP uses torch and
Hugging Face tools. Computational projects add scipy, sympy, and networkx.
Analytics adds pandas, seaborn, statsmodels, and spreadsheet support.
Optional --add sets: notebooks, tracking (wandb), config (Hydra).
These add packages only; configure them in your own code as needed.

Run it:
  cd ../my-research
  uv sync
  uv run python -m project.main
  uv run python -m unittest discover -s tests

Edit configs/experiment.toml to select your input and analysis settings.
The default measurement run uses synthetic example data, not real findings.
Literature review starts with a source-inventory run instead.
The bundled run is a descriptive-analysis smoke test, not an ML training pipeline.
Put your training code in project/algorithms/, datasets in project/datasets/,
and model definitions in project/models/.

Selected packages go into pyproject.toml. uv sync installs them and creates
uv.lock; commit that lockfile for reproducible environments. Python defaults
to 3.12. GPU-specific wheels are not configured automatically.

Folders:
  project/     Runnable Python and analysis code
  configs/     Experiment settings
  tests/       Calculation and configuration checks
  data/        Raw, processed, and synthetic example data
  results/     Separate outputs for each run
  notebooks/   Your own notebooks
  papers/      PDFs and manuscript files
  notes/       Your own notes
  general/     Other project materials
  references/  Source list

List starters:
  uvx --from . sf-template starters

Run directly from GitHub:
  uvx --from git+https://github.com/pranavgundu/sf-template sf-template

Develop this template:
  uv run python -m unittest discover -s tests -v
  uv build

MIT license. The generator has no runtime dependencies. Not published to PyPI.
