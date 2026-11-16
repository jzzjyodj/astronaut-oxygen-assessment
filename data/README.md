# Data directories

- `raw/`: original downloaded files. Preserve their contents and filenames; record publisher metadata and checksums in `artifacts/source_manifest.json`.
- `interim/`: derived tables used during normalization and inspection.
- `processed/`: eligible past-only features and future forecasting targets, prepared within participant partitions.

`processed/forecasting/` contains generated `train.csv`, `validation.csv` and `test.csv`. Recreate them using `.venv/Scripts/python.exe scripts/prepare_forecasting_data.py` after installing the project dependencies. Their source assignments and predictor definitions are recorded in the small JSON manifests under `artifacts/`.

`processed/predictions/` contains validation/test targets and predictions from the fixed persistence/Ridge experiment. These include participant IDs, issue times and forecast boundaries; the two approved CSVs are versioned. The training command reproduces and rewrites the fixed experiment; frontend work should reuse the supplied predictions/model.

The user approved committing the fixed 20 HAPP CSVs, publisher metadata, three forecasting datasets and two prediction datasets directly. These exact files are allowlisted in `.gitignore`; future experiment files, temporary data and other dataset formats remain ignored by default. Keep transformations reproducible in `src/oxygen_assessment/`, called from `scripts/`.

Use the explicit allowlist rather than `git add --force`. Source URLs, license information, checksums and split definitions remain in `artifacts/`. `.gitattributes` preserves asset bytes across checkouts; do not normalize original CSV line endings or overwrite supplied inputs while building the frontend.

The dataset is HAPP: <https://doi.org/10.6084/m9.figshare.29947679>. The local files have been checked against the publisher manifest. Preserve the CC BY 4.0 attribution and the caveat that the publisher already forward filled missing readings. Original CSVs remain unchanged under `raw/`.
