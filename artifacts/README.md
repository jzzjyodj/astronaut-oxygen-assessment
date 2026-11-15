# Computed artifacts

Planned outputs, created only when the corresponding computation runs:

- `source_manifest.json`: dataset provenance, source version/license, downloaded files and checksums.
- `split_manifest.json`: fixed participant assignments and random seed.
- `metrics.json`: actual validation/test errors, baseline comparison, selection rule and support counts.
- `models/`: fitted model/preprocessing files, ignored by Git by default.

Small JSON reproducibility artifacts and aggregate metrics can be committed. Keep observation-level tables and prediction records in the ignored `data/` directories. Demo playback assets are exported separately to `web/public/data/` and are also excluded from Git.
