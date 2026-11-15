# Pipeline entry points

Place the reproducible analysis command here when implementing the pipeline. The planned entry point is `prepare_and_evaluate.py`, importing reusable logic from `src/oxygen_assessment/`.

It should acquire/cache original data, save source and participant manifests, prepare forecasting windows, fit and evaluate the available candidates, and export real frontend assets. It has not been implemented yet.
