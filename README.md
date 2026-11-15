# Oxygen Assessment

A NASA Space Apps prototype for exploring oxygen saturation, heart rate and respiratory rate through historical HAPP research-data replay.

## Project status

This repository currently contains the project structure and planning documents. Data acquisition, analysis, model evaluation, the web application, deployment and the presentation are still to be implemented. No evaluation scores or predictions have been generated here.

## Folder layout

```text
.
├── docs/                       Project context and reference documents
│   ├── handover.md             Copy of the supplied handover
│   ├── project-plan.md         Build order and completion checks
│   ├── data-contract.md        Planned Python-to-frontend interface
│   └── references/             Event guide and other reference material
├── data/
│   ├── raw/                    Original downloaded files; preserve unchanged
│   ├── interim/                Temporary normalized/cleaned data
│   └── processed/              Eligible features and forecasting targets
├── notebooks/                  Exploration and visual checks
├── src/
│   └── oxygen_assessment/      Reusable Python analysis code
├── scripts/                    Reproducible command-line entry points
├── tests/                      Future checks for data and model boundaries
├── artifacts/                  Computed manifests, metrics and model outputs
│   └── models/                 Local fitted model files
├── web/
│   ├── src/                    Frontend components and styles
│   └── public/data/            Small exported datasets used by the demo
├── reports/
│   ├── figures/                Charts and real prototype screenshots
│   └── slides/                 Seven-slide deck and presentation exports
├── pyproject.toml              Python package and dependencies
└── .gitignore                  Local environments, data caches and build files
```

## Start here

1. Read `docs/project-plan.md` and consult `docs/handover.md` for detailed context.
2. Establish a minimal frontend and a working public deployment path.
3. Implement data acquisition and analysis in `src/oxygen_assessment/`, with one entry point in `scripts/`.
4. Export computed results to `artifacts/` and a small playback payload to `web/public/data/`.
5. Build the assessment and evidence views; finish and verify the deck and public demo.

## Python environment

From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

For future automated checks, install the development dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
```

The package declares NumPy, pandas and scikit-learn. Nothing is installed by creating this scaffold. Record resolved dependency versions when the analysis first runs successfully. Frontend dependencies will be defined in `web/` when its stack is initialized.

## Data and results conventions

- Keep original downloads in `data/raw/`; record source, version, license and checksums in a generated `artifacts/source_manifest.json`.
- Keep every participant in one partition. Save the chosen split in `artifacts/split_manifest.json` before fitting models.
- Save actual evaluation results in `artifacts/metrics.json`; do not create example scores that could be mistaken for results.
- Keep reusable processing in Python modules; use notebooks for exploration and explanation.
- Commit small reproducibility artifacts such as source manifests, split definitions and aggregate metrics. All datasets, fitted model files and generated browser playback data stay local and are excluded from Git. Dataset formats such as CSV and Parquet are also ignored elsewhere in the project.
- Regenerate `web/public/data/demo.json` locally or during deployment from the public source. Hosting the demo's selected playback records is a separate deployment step; dataset files are not stored in the source repository.
- Generated artifacts should be reproducible from the original inputs and saved configuration.
- Markdown notes under `docs/references/` (or `docs/reference/`) stay local and are excluded from Git. Project documentation elsewhere in `docs/` remains eligible for version control.

## Product boundaries

HAPP contains terrestrial chamber observations from volunteers, not astronaut telemetry. The intended prediction is mean SpO2 over the next 30 seconds using the preceding 60 seconds. The product is a research prototype, with no established clinical validation. User-entered context must remain separate from measured data and precomputed forecasts.
