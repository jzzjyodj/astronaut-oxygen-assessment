# Assessment and frontend export contract

Contract version 1, specified 15 November 2026. This specifies the future playback exporter and frontend; it does not implement them. See `assessment-workflow.md` for exact behavior, prompt wording and acceptance cases. The existing fitted model, split and evaluation remain fixed.

## Information origins

| `provenance` value | Visible label | Meaning |
| --- | --- | --- |
| `recorded_measurement` | Recorded measurement | Released HAPP observation, not astronaut telemetry |
| `calculated_change` | Calculated change | Arithmetic over identified recorded readings |
| `model_forecast` | Model forecast | Saved Ridge pipeline output |
| `model_derived_insight` | Model-derived insight | Model/observation comparison, contribution or forecast-history calculation |
| `user_entered_context` | User-entered context | Demonstration input, not matched research data |
| `sourced_guidance` | Sourced guidance | Educational text with reviewed references |
| `review_prompt` | Review prompt | Authored application rule with identified evidence |
| `evaluation_result` | Evaluation results | Saved validation/test performance calculations |
| `compiled_summary` | Compiled summary | Compilation retaining each component's provenance |

Attach provenance at section/record level where useful for compactness, retaining visible, unambiguous labels. Every review prompt identifies its rule ID, triggering evidence references and linked guidance. Never relabel a rule as a model output or an agency instruction.

## Playback payload: `web/public/data/demo.json`

Playback exports remain excluded from Git. Keep source manifests and aggregate evaluation separate from observation-level records.

| Field | Required contents |
| --- | --- |
| `metadata` | Schema version, source title/URL/version/license, origin badge, selected method, target definition, split description, and model/split/preparation/selection/metrics checksums |
| `participants` | Held-out **test** participant IDs and full recorded series for replay |
| `forecasts` | Existing forecasts with original issue/window metadata, recorded issue-time reading, difference and grouped contributions; no observed future targets |
| `evaluation` | Actual validation/test MAEs, aggregation, units, participant counts/errors and persistence comparison from `artifacts/metrics.json`; provenance `evaluation_result` |

Each participant series entry has `elapsed_s` (integer study seconds), `spo2`, `heart_rate` and `respiratory_rate` (finite number or null), with provenance `recorded_measurement`. Units are %, beats/min and breaths/min. Zero is a measurement, not an unknown sentinel. First observation time is zero. Do not fabricate dates, live connectivity or per-reading reliability/imputation labels.

The browser may receive full series for replay but displays/summarizes only readings at or before cursor c. Apply this bound to plotted values, text alternatives, tooltips and downloads. Future observed target means (`target_mean_spo2`) are omitted from assessment exports; evaluation retains aggregate errors separately.

## Forecast and explanation record

| Field | Meaning / provenance |
| --- | --- |
| `participant_id`, `issue_time_s` | Participant and original issue second |
| `forecast_start_s`, `forecast_end_s` | Issue +1 and +30, inclusive |
| `method` | `ridge`, from the frozen validation selection |
| `predicted_mean_spo2` | Saved next-window mean; `model_forecast` |
| `recorded_spo2_at_issue` | Exact issue-time reading; `recorded_measurement`; null if unavailable |
| `predicted_mean_minus_issue_spo2` | Forecast minus that reading, in percentage points; `model_derived_insight`; null if either is unavailable |
| `explanation` | Reference and grouped contributions below; `model_derived_insight`; null if unavailable |

The explanation has `reference_prediction` (fitted intercept, SpO2 %) and `group_contributions` with `spo2`, `heart_rate` and `respiratory_rate` (signed percentage points). Multiply each fitted coefficient by the saved scaler-transformed feature value in the preparation manifest's predictor order. Sum by feature prefix. Reference plus all three groups must reproduce the saved prediction within 1e-10 percentage points before export. A reconstruction failure is an export verification error, not permission to invent or rebalance contributions.

Use existing predictor tables and the fitted pipeline; do not refit or include context. Link explanation provenance to model checksum and feature definitions. The reference is the model quantity at its training feature means, not a personal normal reading. Contributions describe arithmetic with correlated inputs, not causes or an ablation study.

Warm-up forecasts may be absent. A present unavailable prediction uses null, never a numerical placeholder. Issues start at 59 and advance in five-second steps. Preserve scalar target means; no invented full trajectory or confidence band based on overall MAE.

## Snapshot calculations and time boundaries

- Snapshot key: JSON-encode `[participant_id, replay_time_s]`; time is a non-negative integer elapsed second.
- Observed change: reading at c minus reading at c-30, with both times and provenance `calculated_change`. Unavailable results use null and `insufficient_history`, `missing_current_reading` or `missing_prior_reading` as appropriate.
- Active forecast: latest record issued <=c, finite prediction, and c < forecast_end_s. A missing latest prediction does not silently fall back to an older record. Keep reasons explicit: `warmup`, `missing_forecast`, `expired`.
- Age: c minus issue time. Difference uses the reading at that issue, not a later cursor reading. Never shift target endpoints.
- Past forecast history: finite estimates issued during [max(0,c-60),c], inclusive, for this participant only, ordered by issue. Include original target intervals; expired estimates can remain historical points.
- Evolution: for active issue i, compare its value with the finite estimate issued exactly at i-30. Include both issue/window records and signed difference, provenance `model_derived_insight`. Otherwise return null with `insufficient_forecast_history`. Do not interpolate or use a future issue.
- Keep full precision. Direction wording rounds to one decimal place, halves away from zero, and normalizes negative zero. This carries no clinical threshold meaning.

## User context and review rules

Context is local session state, never part of the shipped playback dataset or predictor matrix. Every draft includes its snapshot key, provenance `user_entered_context`, and:

| Field | Allowed values / default |
| --- | --- |
| `symptoms_status` | `unknown` (default), `none_reported`, `reported` |
| `symptom_note` | Text, empty by default |
| `activity_context` | Text, empty by default |
| `measurement_reliability` | `unknown` (default), `no_concerns_reported`, `concerns_reported` |
| `measurement_note` | Text, empty by default |
| `responder_note` | Text, empty by default |

Use a session-memory map keyed by snapshot. New snapshots get independent defaults; revisiting restores only that key's draft. Return copies to prevent shared mutation. Refresh discards drafts. Do not persist to local storage, transmit context, mutate replay/model records or treat notes as HTML.

Implement prompts from the ordered rule table in `assessment-workflow.md`. Each carries `rule_id`, `provenance: review_prompt`, resolved text, evidence references with their own provenance, and a guidance card ID or form target. Numerical decrease rules use the displayed signed difference and non-negative magnitude X. Missing data cannot trigger a decrease. No rule determines clinical urgency, confidence, diagnosis or all-clear status.

## Educational content: `web/public/data/guidance.json`

This committed content file is not a dataset. Root fields: `schema_version`, `reviewed_on`, `review_status`, `available_independently_of_forecast`, `sources`, `cards`. Sources have stable IDs, title, publisher, URL, review date, applicable sections and observed update date (null when unavailable).

Cards have `id`, `title`, `provenance: sourced_guidance`, `body`, `source_ids`, `reviewed_on`, `applicability`. Resolve IDs through the bundled sources and show actual links. All cards remain accessible without a forecast/context. Source checking is not clinical review or mission approval. The absence of a supplied mission procedure is a prototype status statement, not an agency assertion.

Card IDs: `understand-spo2`, `measurement-quality`, `symptoms-trends`, `spaceflight-context`, `consultation-help`. Source IDs: `fda-pulse-oximeter-basics`, `nasa-hypoxia`, `nasa-distance-from-earth`. Rule guidance references must resolve.

## Compiled summary and evidence view

The eventual local plain-text/JSON summary includes the source/license badge, participant/replay time, available readings/changes, active forecast and all available insights with original issue/window metadata, past forecasts bounded by c, context, prompts/evidence references, unknowns and guidance references. Its origin is `compiled_summary`; retain original provenance on every component. Identify historical research replay and user-entered demonstration context.

Exclude future outcomes, later-issued forecasts, expired estimates as active predictions, clinical severity, treatment instructions and invented confidence intervals. Download does not contact medical support. The separate evidence view presents existing MAE and limitations as Evaluation results, not an individual forecast's uncertainty or clinical safety guarantee.
