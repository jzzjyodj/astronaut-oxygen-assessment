# Computed artifacts

Outputs are created only when the corresponding computation runs:

- `data_quality.json`: aggregate dataset checks, per-participant profiles and explicit limitations; no observation-level records.
- `source_manifest.json`: dataset provenance, source version/license, downloaded files and checksums.
- `split_manifest.json`: fixed participant assignments and random seed.
- `forecast_preparation.json`: the ordered predictor list, precise feature/window definitions, per-partition/per-participant counts, environment versions and exported dataset checksums. No observation-level records are included.
- `metrics.json`: actual validation/test errors, baseline comparison, selection rule and support counts.
- `model_selection.json`: validation-only selection, method settings, feature list, training coverage, environment versions and input/model checksums, saved before test targets are loaded.
- `assessment_contract_verification.json`: saved-model explanation/content checks and reference scenario results, with actual frontend integration checks explicitly pending.
- `models/`: fitted model/preprocessing files, ignored by default except the approved `ridge_pipeline.pkl` handover asset.

The fitted scaler/Ridge pipeline is versioned as `models/ridge_pipeline.pkl`. The two approved prediction CSVs are versioned under `data/processed/predictions/` so teammates can reuse the fixed experiment without retraining.

JSON reproducibility artifacts, aggregate metrics and the approved scientific assets are committed. Future experimental data/models remain ignored by default. `.gitattributes` preserves exact asset and linked-JSON bytes. Browser playback assets will be exported separately to `web/public/data/` and remain excluded under the current policy.
