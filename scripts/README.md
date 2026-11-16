# Pipeline entry points

`check_data_quality.py` audits local CSVs and exports aggregate quality/provenance artifacts. Run it with `.venv/Scripts/python.exe scripts/check_data_quality.py`. Add `--fetch-metadata` to retrieve the publisher manifest for checksum verification; otherwise it uses the locally cached metadata when present.

`prepare_forecasting_data.py` runs the source audit, freezes/reuses the 12/4/4 split and exports 19 unscaled features with next-30-second mean SpO2 targets. Run it with `.venv/Scripts/python.exe scripts/prepare_forecasting_data.py`. It writes the approved, versioned datasets and preparation manifests. It stops if frozen sources change and performs no model fitting or evaluation.

`train_and_evaluate.py` verifies prepared inputs, fits one training-only scaler/Ridge pipeline, selects on participant-average validation MAE and evaluates both methods on test participants. Run it with `.venv/Scripts/python.exe scripts/train_and_evaluate.py`. The saved model, metrics, selection and prediction CSVs are versioned handover assets; frontend work should reuse them rather than retrain. Selection is frozen before test target loading.

There is no combined `prepare_and_evaluate.py` entry point. The frontend playback exporter is also still to be implemented; the root teammate handover describes its inputs/output contract.

`verify_assessment_contract.py` checks contribution reconstruction against all saved test forecasts, exact issue-time readings, guidance reference integrity and reference replay/context scenarios. It saves an aggregate verification record while preserving the model, split, selection and evaluation. It is a specification verifier, not a frontend implementation or browser test.
