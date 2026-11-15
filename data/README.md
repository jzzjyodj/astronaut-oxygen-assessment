# Data directories

- `raw/`: original downloaded files. Preserve their contents and filenames; record publisher metadata and checksums in `artifacts/source_manifest.json`.
- `interim/`: derived tables used during normalization and inspection.
- `processed/`: eligible past-only features and future forecasting targets, prepared within participant partitions.

All contents under `data/`, including future subdirectories, are ignored by Git except `README.md` documentation and `.gitkeep` directory markers. Common dataset formats are also ignored elsewhere in the project. Keep acquisition and transformations reproducible in `src/oxygen_assessment/`, called from `scripts/`.

Do not use `git add --force` to add datasets. Commit source URLs, license information, checksums and split definitions in `artifacts/` instead. These records describe the data without uploading observations.

The intended dataset is HAPP: <https://doi.org/10.6084/m9.figshare.29947679>. The handover records CC BY 4.0 licensing and prior forward filling by the publisher. Capture the metadata used by the actual download and preserve those caveats. No dataset has been downloaded into this scaffold.
