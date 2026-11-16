# Oxygen Assessment

A NASA Space Apps prototype for exploring oxygen saturation, heart rate and respiratory rate through historical HAPP research-data replay.

**Frontend teammate: start with [handover_context.md](handover_context.md).** The selected datasets, predictions and fitted model are committed directly so a clone includes the existing analysis assets.

## Project status

The project structure, local Python environment, data quality audit, frozen participant split, forecasting examples and persistence/Ridge experiment are implemented. The approved 20 HAPP CSV files, generated features, prediction datasets and fitted model are included in Git for teammate handoff. Ridge was selected using validation MAE, followed by evaluation on the four test participants. The web application, deployment, frontend playback export and presentation are still to be implemented.

The assessment workflow and information origins are specified in [docs/assessment-workflow.md](docs/assessment-workflow.md). Five source-checked educational cards are bundled in `web/public/data/guidance.json`; the planned playback, model-insight and context interfaces are defined in [docs/data-contract.md](docs/data-contract.md). These define the next frontend/export implementation; the browser workflow is not implemented yet.

Run `.venv/Scripts/python.exe scripts/verify_assessment_contract.py` to verify contribution reconstruction against saved forecasts, issue-time comparisons, guidance references and reference contract scenarios. The aggregate result is saved in `artifacts/assessment_contract_verification.json`, with future browser checks explicitly marked pending. This command does not fit models or modify existing experiment artifacts.

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

The local environment uses Python 3.13.13, selected by `.python-version`. Commands use the environment's executable directly, so shell activation is optional. The package declares NumPy, pandas and scikit-learn; the development extra adds pytest. `requirements.lock.txt` records the installed dependency versions for this Python environment. Frontend dependencies will be defined in `web/` when its stack is initialized.

To recreate the recorded dependencies after creating a Python 3.13 environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

## Run data quality checks

```powershell
.\.venv\Scripts\python.exe scripts/check_data_quality.py
```

The audit reads all CSVs under `data/raw/` without modifying them. It checks schema, missing cells, numeric validity, duplicate rows and timestamps, one-second continuity, participant file coverage and publisher checksums when metadata is available. It writes aggregate results to `artifacts/data_quality.json` and provenance to `artifacts/source_manifest.json`.

The cached publisher metadata is included as `data/raw/happ_metadata.json`. To fetch or refresh it and then run the audit:

```powershell
.\.venv\Scripts\python.exe scripts/check_data_quality.py --fetch-metadata
```

Run the synthetic boundary checks for the audit code with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The released dataset was already forward filled by its authors. A complete local file does not establish complete original sensor measurements. These checks establish structural fitness for the next analysis step, not clinical validity.

## Prepare forecasting data

```powershell
.\.venv\Scripts\python.exe scripts/prepare_forecasting_data.py
```

This command reruns the existing quality checks on current sources, then creates or reuses `artifacts/split_manifest.json`. Participant IDs are sorted and shuffled with NumPy's `default_rng(42)`, assigning 12 to training, 4 to validation and 4 to testing. The manifest records source SHA256 checksums. Existing assignments are preserved; changed participant membership, source contents or source paths stop the run without replacing the generated datasets.

Each participant is processed separately at one observation per second. Elapsed time starts at zero. The first forecast issue time is second 59, followed by 64, 69 and so on. History covers t-59 through t; the target is mean SpO2 over t+1 through t+30. Incomplete boundary windows are excluded. The pipeline does not scale inputs or fit models.

| Partition | Participants | Examples in the current HAPP release |
| --- | ---: | ---: |
| Training | 12 | 19,107 |
| Validation | 4 | 6,477 |
| Test | 4 | 5,786 |
| Total | 20 | 31,370 |

The command writes `train.csv`, `validation.csv` and `test.csv` under `data/processed/forecasting/`. These three approved datasets are versioned for teammate handoff. `artifacts/forecast_preparation.json` contains settings, the ordered list of 19 predictor columns, definitions, counts, CSV checksums and the split manifest checksum.

The 19 predictors are current value, 60-second mean, population standard deviation (`ddof=0`), changes over 10/30 seconds and 60-second ordinary least squares slope for each of the three signals, plus the 60-second SpO2 minimum. A change is the current value minus the value at t-10 or t-30; slope uses seconds 0 through 59 with an intercept. The prediction table also contains participant ID, partition, issue time, history/forecast boundaries and `target_mean_spo2`; these metadata/target columns are excluded from the saved predictor list. Use that explicit list when fitting later models.

Overlapping windows are correlated. Participant separation is preserved throughout preparation; these examples do not represent 31,370 independent people. The command reads cached metadata when available and requires no network access.

## Train and evaluate

```powershell
.\.venv\Scripts\python.exe scripts/train_and_evaluate.py
```

The command verifies the prepared dataset checksums, column definitions and participant membership. It fits `StandardScaler` and `Ridge(alpha=1.0, solver="svd", fit_intercept=True)` on the 19,107 training examples from 12 participants, with equal weight per example. Persistence predicts the current SpO2. The models and scaler are not refitted on validation or test participants.

Validation selects the lower participant-average MAE; persistence wins numerical ties within `1e-12` SpO2 percentage points. The method, configuration, input checksums and fitted pipeline are saved before test targets are parsed. Both methods are then evaluated on the test partition; that comparison does not change the selected method. Predictions are raw and unclipped. No parameter search, cross-validation or synthetic training augmentation was performed.

### Actual results

MAE is calculated for each participant, then averaged equally across the four participants in each partition. Units are **SpO2 percentage points**. Ridge's absolute improvement is persistence MAE minus Ridge MAE.

| Partition | Participants | Examples | Persistence MAE | Ridge MAE | Ridge absolute improvement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 4 | 6,477 | 0.576830 | 0.502003 | +0.074827 |
| Test | 4 | 5,786 | 0.574573 | 0.479397 | +0.095176 |

**Selected method: Ridge, based on validation results.** The final test comparison uses the same training-fitted pipeline.

| Test participant | Examples | Persistence MAE | Ridge MAE |
| --- | ---: | ---: | ---: |
| 0610b | 1,424 | 0.467388 | 0.380446 |
| 0626a | 1,503 | 0.926547 | 0.761870 |
| 0715a | 1,315 | 0.506307 | 0.419288 |
| 0722b | 1,544 | 0.398051 | 0.355983 |

Full-precision validation/test results and every participant's score are in `artifacts/metrics.json`. `artifacts/model_selection.json` records the decision before test evaluation, linking to the feature preparation, split and dataset checksums. The scaler/Ridge pipeline is versioned as `artifacts/models/ridge_pipeline.pkl`. The two approved validation/test prediction CSVs are versioned under `data/processed/predictions/`, with issue times, window boundaries, targets, current SpO2, both predictions and the selected prediction.

These results describe four test participants from the HAPP terrestrial chamber study. Overlapping windows, publisher forward filling and limited population coverage constrain interpretation. They do not establish clinical, astronaut, prospective or external-cohort effectiveness. Rerunning reproduces this experiment; it does not provide additional independent validation.

## Data and results conventions

- Keep original downloads in `data/raw/`; record source, version, license and checksums in a generated `artifacts/source_manifest.json`.
- Keep every participant in one partition. Save the chosen split in `artifacts/split_manifest.json` before fitting models.
- Save actual evaluation results in `artifacts/metrics.json`; do not create example scores that could be mistaken for results.
- Keep reusable processing in Python modules; use notebooks for exploration and explanation.
- The user-approved fixed HAPP CSVs/metadata, three feature datasets, two prediction datasets and fitted Ridge pipeline are explicitly allowlisted in Git alongside reproducibility manifests and aggregate results. Future experimental outputs remain ignored by default.
- Preserve exact bytes of scientific assets and checksum-linked artifact JSON; `.gitattributes` disables automatic newline conversion for them.
- Generate `web/public/data/demo.json` locally or during deployment from the committed assets. The browser export remains ignored; ensure it is included in the deployed static build.
- Generated artifacts should be reproducible from the original inputs and saved configuration.
- Markdown notes under `docs/references/` (or `docs/reference/`) stay local and are excluded from Git. Project documentation elsewhere in `docs/` remains eligible for version control.

## Product boundaries

HAPP contains terrestrial chamber observations from volunteers, not astronaut telemetry. The intended prediction is mean SpO2 over the next 30 seconds using the preceding 60 seconds. The product is a research prototype, with no established clinical validation. User-entered context must remain separate from measured data and precomputed forecasts.
