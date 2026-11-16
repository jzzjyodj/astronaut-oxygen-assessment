# Frontend teammate handover: Oxygen Assessment

Updated 15 November 2026, America/Toronto. Start here after cloning. This document describes the current implemented analysis and the agreed product design. Detailed implementation contracts are linked below. The earlier [planning handover](docs/handover.md) is background; its statement that no model exists is historical.

## 1. Problem and agreed scope

**Help astronauts assess changes in oxygen saturation and related physiological measurements, understand what needs attention, and access clear guidance when immediate medical consultation is unavailable.**

Build an accessible oxygen-assessment research prototype using real HAPP terrestrial chamber observations, user-entered demonstration context and source-linked guidance. Keep **Research-data replay · terrestrial chamber study** visible. There is no approved product name beyond the descriptive working title Oxygen Assessment.

The product supports understanding changes, reviewing relevant information and compiling a consultation summary. It does not supply a learned medical urgency assessment, diagnosis or mission-approved treatment procedure. No live wearable integration, backend inference service, chatbot, login or database is required. Keep the focus on oxygen assessment; adding VTaC or every spaceflight hazard is outside the agreed build.

The final project deliverables are a **working public prototype URL and a seven-slide deck**. The remaining work should prioritize the user journey and usable public access over additional modelling.

## 2. What is implemented, and what remains

| Implemented and included in the repository | Remaining frontend/package work |
| --- | --- |
| Original HAPP CSVs and publisher metadata | Export browser playback JSON from the supplied assets |
| Reproducible quality audit and source checksums | Initialize the static web application |
| Frozen participant split and 19-feature datasets | Build Assessment and Evidence views |
| Training-fitted Ridge/scaler, saved predictions, actual metrics | Implement the three model insights in the interface |
| Workflow specification and data contract | Implement context drafts, review prompts and summary download |
| Five source-checked educational guidance cards | Verify accessibility, replay boundaries and real user flow |
| Unit/integration tests and model-explanation verification | Deploy publicly, verify signed-out access, package the deck |

The frontend and `web/public/data/demo.json` **do not exist yet**. There is no combined `prepare_and_evaluate.py` command; the existing commands below are separate, working steps. Contribution explanations have been mathematically verified but have not yet been packaged into browser records.

## 3. Clone and begin without retraining

```powershell
git clone https://github.com/jzzjyodj/astronaut-oxygen-assessment.git
cd astronaut-oxygen-assessment
git switch -c frontend/prototype
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe scripts/verify_assessment_contract.py
```

Use **Python 3.13.13**; `.python-version` selects it for pyenv users, but does not install Python automatically. The lock records NumPy 2.5.5, pandas 3.1.1 and scikit-learn 1.9.1 plus their dependencies and pytest. The commands above are for Windows PowerShell; on macOS/Linux use `.venv/bin/python` for the equivalent commands. Shell activation is optional. The editable install may need network access for its build dependency.

The selected raw data, feature tables, predictions and saved model are committed directly. A normal clone supplies them; no asset ZIP or retraining is needed. `.gitattributes` preserves their exact bytes because publisher/experiment checksums depend on them. Do not let an editor or formatter normalize these files' line endings.

The contract verifier reads existing assets without fitting. It checks all 5,786 test forecasts, reconstructs contributions, validates issue-time readings and checks reference replay/context cases. It updates only its aggregate verification report. It is not a browser test.

Run existing tests if needed:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The last completed suite had **20 passing tests**. A fresh environment may take time on the first scientific-library import.

## 4. Dataset, preprocessing and quality

HAPP: *High-Altitude Pilot Physiological Monitoring Dataset: Respiratory Performance and SpO2 Analysis*, version 1. [Dataset](https://doi.org/10.6084/m9.figshare.29947679), [publisher manifest](https://api.figshare.com/v2/articles/29947679), [paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12886808/).

The dataset license is **CC BY 4.0**: retain attribution to Chunyang Jia, Meng Yang and Chuangang Zhao, link the dataset and license, and identify derived processing. The paper has its own publication license; do not assume it matches the dataset license. Dataset license/source metadata are retained in [source_manifest.json](artifacts/source_manifest.json).

- **20 participant files; 158,580 observations; 44.05 hours at 1 Hz; 6,771,096 original CSV bytes.**
- Healthy male volunteers aged 18–40 in a controlled terrestrial hypobaric chamber; these are not astronauts.
- Columns: `Altitude`, `Time`, `SPO2`, `Heart rate`, `Respiratory rate`, `O2`, `N2`, `CO2`, `other`.
- All 20 publisher MD5 values matched. The released files have no missing cells, duplicate rows/timestamps, backward steps, gaps greater than one second or invalid numeric values under the implemented mathematical checks.
- **The publisher already forward filled missing values.** No individual imputation mask is available. We performed no additional imputation, clipping, smoothing, outlier deletion or synthetic augmentation.
- `Time` is clock time, sometimes with a single-digit hour. Audit code accepts that format and verifies contiguous one-second order. Processing uses relative elapsed seconds from each participant's first observation; no mission dates are invented.
- Observed ranges: SpO2 70–100%, heart rate 43–179 beats/min, respiratory rate 4–35 breaths/min. These describe the dataset; they are not alert thresholds.
- Altitude and mask gas composition are experimental context. They are excluded from the model and must not be relabelled as spacecraft cabin conditions.

Relevant code: [quality.py](src/oxygen_assessment/quality.py), [quality results](artifacts/data_quality.json).

## 5. Split and forecasting-example preparation

Sort participant IDs, shuffle once using `numpy.random.default_rng(42)`, assign 12/4/4 participants and freeze their assignments/source SHA256 checksums in [split_manifest.json](artifacts/split_manifest.json). Existing assignments are reused; changed membership or sources stop preparation rather than silently reshuffling.

| Partition | Participants | Examples |
| --- | ---: | ---: |
| Training | 12 | 19,107 |
| Validation | 4 | 6,477 |
| Test | 4 | 5,786 |
| Total | 20 | 31,370 |

For each participant independently, issue an example at elapsed second 59, then 64, 69 and so on. At issue t, use **60 observations from t-59 through t**. The target is **mean SpO2 across t+1 through t+30 inclusive**. Discard incomplete boundary windows. Overlapping windows are correlated; 31,370 examples do not represent that many independent people.

The 19 features are:

| Signal | Features |
| --- | --- |
| SpO2 | Current, 60-second mean/minimum/population standard deviation, 10-/30-second changes, 60-second slope |
| Heart rate | Current, 60-second mean/population standard deviation, 10-/30-second changes, 60-second slope |
| Respiratory rate | Same six features as heart rate |

Standard deviation uses `ddof=0`; a change is current minus t-10 or t-30; slope is ordinary least squares against seconds 0–59 with an intercept. No future observations, centered windows, participant IDs, raw clock times, context fields or beat-to-beat HRV enter the predictors. There are no beat-to-beat intervals for HRV.

Prepared CSVs live in `data/processed/forecasting/`. [forecast_preparation.json](artifacts/forecast_preparation.json) contains the exact ordered `feature_columns`, definitions, metadata/target columns, counts and dataset checksums. Use that predictor list, never all numeric columns. [forecasting.py](src/oxygen_assessment/forecasting.py) implements preparation.

## 6. Model and actual results

**Persistence** predicts the current SpO2 as the next-30-second mean. **Ridge** uses `StandardScaler` followed by `Ridge(alpha=1.0, solver="svd", fit_intercept=True)`.

Scaling and Ridge were fitted once on the 19,107 training examples only, with equal weight per example. Validation selected the lower participant-average MAE; persistence wins numerical ties within 1e-12 percentage points. Selection/configuration/input checksums were saved before test targets were parsed. The same training-fitted pipeline was evaluated on test; there was no train+validation refit, tuning or cross-validation.

MAE is calculated within each participant, then averaged equally across the four participants. Units are **SpO2 percentage points**, not accuracy percentages.

| Partition | Persistence MAE | Ridge MAE | Absolute Ridge improvement |
| --- | ---: | ---: | ---: |
| Validation | 0.576830 | 0.502003 | +0.074827 |
| Test | 0.574573 | 0.479397 | +0.095176 |

**Selected method: Ridge, based on validation.** Its test average error is about 0.48 percentage points for this task. This is not an individual prediction bound, worst-case guarantee, clinical effectiveness result or claim of superiority to studies with different targets.

| Test participant | Examples | Persistence MAE | Ridge MAE |
| --- | ---: | ---: | ---: |
| 0610b | 1,424 | 0.467388 | 0.380446 |
| 0626a | 1,503 | 0.926547 | 0.761870 |
| 0715a | 1,315 | 0.506307 | 0.419288 |
| 0722b | 1,544 | 0.398051 | 0.355983 |

Full precision and validation participant results: [metrics.json](artifacts/metrics.json). Frozen choice/model checksum: [model_selection.json](artifacts/model_selection.json). Fitted pipeline: `artifacts/models/ridge_pipeline.pkl`. Predictions: `data/processed/predictions/validation.csv` and `test.csv`. [modeling.py](src/oxygen_assessment/modeling.py) implements the experiment.

Four test participants, one controlled population, overlapping windows and publisher forward filling limit the evidence. We have not established sharp-drop detection, clinical urgency, astronaut performance, prospective effectiveness, per-prediction uncertainty, or causal effects of heart/respiratory rate. The test results have already been observed; frontend work must not become test-driven model tuning.

## 7. Three model insights to expose

1. **Forecast difference:** predicted next-window mean minus recorded SpO2 at the issue time. Display the two values and signed percentage-point difference. At an intermediate replay cursor, retain the original issue-time comparison and show forecast age.
2. **Contribution explanation:** transform the exact 19 features using the saved training scaler; multiply standardized values by fitted coefficients; sum by `spo2_`, `heart_rate_`, `respiratory_rate_` prefixes. Show fitted intercept plus three signed group contributions. Their sum must reconstruct the saved forecast within 1e-10 percentage points. This is model arithmetic relative to its training reference, not personal normality, causation or evidence from a signal-ablation experiment.
3. **Forecast evolution:** show finite estimates already issued during the preceding 60 seconds. Compare the latest active estimate with the one issued exactly 30 seconds earlier when available. They concern successive target windows; do not draw an invented future physiological trajectory.

[Assessment verification](artifacts/assessment_contract_verification.json) checked all 5,786 test forecasts. Maximum reconstruction discrepancy was approximately 1.42e-14 percentage points. This verifies arithmetic/reference cases, not browser behavior or clinical validity.

## 8. Read these app specifications

| File | How to use it |
| --- | --- |
| [Assessment workflow](docs/assessment-workflow.md) | User journey, exact review-prompt rules, context defaults, insight behavior, summary requirements and acceptance cases |
| [Data contract](docs/data-contract.md) | Export fields, units, provenance, timing, missingness and snapshot-state rules |
| [Guidance content](web/public/data/guidance.json) | Five educational cards with source links, review dates and applicability |
| [Web overview](web/README.md) | Intended two-view static product |

Keep these information origins visibly distinct:

| Origin label | Source |
| --- | --- |
| Recorded measurement | Released HAPP observations |
| Calculated change | Arithmetic over past recorded readings |
| Model forecast / Model-derived insight | Ridge output and computations using the model |
| User-entered context | Demonstration input scoped to one snapshot, not HAPP ground truth |
| Sourced guidance | FDA/NASA educational resources |
| Review prompt | Our deterministic application rule, not a learned/agency-approved medical assessment |
| Evaluation results / Compiled summary | Experiment calculations / compilation retaining each component's origin |

The Assessment view should support **readings → forecasts → context → review/explanations → downloadable summary**. The Evidence view shows provenance, actual MAE/baseline comparison, method and limits. Keep help/guidance accessible without waiting for a forecast.

Use the exact context defaults/rules in the specifications. Symptoms and reliability default unknown. Drafts are session-memory entries keyed by participant and replay time; a new snapshot starts unknown, returning restores its own draft, refresh clears drafts. Context never changes the recorded data or forecasts. There is no transmission to medical support.

## 9. First teammate task: implement the playback exporter

Build an offline Python exporter using the committed assets; do not require live Python inference in the browser. Follow the existing data contract and add a documented command such as `scripts/export_frontend_data.py`.

Inputs:

- `artifacts/split_manifest.json` for test participant IDs: **0610b, 0626a, 0715a, 0722b**.
- Corresponding original CSVs under `data/raw/` for actual recorded series and elapsed times.
- `data/processed/predictions/test.csv` for issue/window metadata and `selected_prediction`.
- `data/processed/forecasting/test.csv` for the exact 19 explanation inputs.
- `artifacts/models/ridge_pipeline.pkl` for scaler, coefficients and intercept.
- Preparation, selection and metrics manifests for schema/checksum validation and the Evidence view.

Output: `web/public/data/demo.json`, with source/model metadata, test participant series, forecasts and grouped contributions, and aggregate evaluation as specified. The committed `guidance.json` is a separate content asset. Omit observed future target means from assessment export records. If full recorded series are shipped for replay, the frontend must hide future observations from charts, text, tooltips and summaries until the cursor reaches them.

The browser should consume the scalar next-window mean, not a fabricated 30-point prediction curve. Do not turn MAE into a confidence band. At cursor c, the latest issue <=c is active only while c < forecast_end_s; show its original window and age. First issue is 59. Compare forecasts to the issue-time reading, never silently to a later reading. Nulls and warm-up remain explicit.

The future `demo.json` is currently ignored by Git. Generate it before the static build/deployment and ensure it is included in the deployed build. The teammate can define a reproducible exporter/build command; do not silently change Git policy or require judges to run Python.

## 10. Frontend, accessibility and deployment

Use a static web stack; React/Vite is a suggested fast path, not an already initialized project. The browser can replay precomputed data. No API key or remote model call is needed.

Implement the specified two views with participant/replay controls, three measurement cards, observed oxygen trend, three forecast insights, educational cards, context form, rule-driven review prompts and local text/JSON summary download.

Make controls large and labelled, support keyboard-only use and visible focus, keep text/contrast readable, show units, supplement color with text, and provide a text alternative for charts. Test at desktop and narrow/mobile widths. Avoid presenting green/healthy/all-clear states or unsupported clinical thresholds.

Acceptance cases include warm-up; missing readings; forecast expiry; cursor positions between issues; future-data exclusion; separate snapshot drafts; missing forecast-evolution history; correct one-decimal direction wording; and summaries retaining provenance/unknowns. Contribution reconstruction and source checksums must pass. The reference verifier is not a substitute for these browser checks.

Establish a working public static deployment early. Ensure the final deployed page contains the real generated playback asset, opens without sign-in and does not expose code-only placeholders. A hosted static page is not automatically an offline/PWA application; claim only behavior actually tested.

Package the seven-slide story: problem, NASA relevance, walkthrough, data/method, actual results, value/limits, and public demo/team/sources. Use screenshots from the real working app. Recheck active submission requirements and deadline; no active deadline has been reverified in this handover.

## 11. Reproducibility commands and collaboration

The following are existing analysis commands, provided for inspection/reproduction rather than required frontend setup:

```powershell
.\.venv\Scripts\python.exe scripts/check_data_quality.py
.\.venv\Scripts\python.exe scripts/prepare_forecasting_data.py
.\.venv\Scripts\python.exe scripts/train_and_evaluate.py
```

The training command reproduces the fixed experiment and rewrites fitted/result artifacts. Routine frontend work should reuse the supplied model/results instead. Repeated evaluation of the same test set is not additional independent validation. Do not revise model settings based on known test scores.

Push your implementation to this repository on your branch:

```powershell
git status
git add <reviewed-code-and-documentation-paths>
git commit -m "Build accessible oxygen assessment prototype"
git push -u origin frontend/prototype
```

Review staged changes and open a pull request to `main`. Pushing needs repository write access; this handover does not grant it. Coordinate if the branch already exists. The approved raw CSVs, feature tables, saved predictions and Ridge model are now explicitly versioned. Future experiment outputs, environments, caches and reference-folder Markdown remain ignored. Keep unexpected reference downloads out of commits.

The latest user decisions override historical guidance that all data/model files must stay outside Git. The selected asset exceptions are explicit in `.gitignore`; exact-byte preservation is in `.gitattributes`. Preserve the recorded source/model checksums and avoid accidentally rewriting the scientific artifacts while working on presentation.
