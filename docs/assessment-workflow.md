# Oxygen assessment workflow

Status: workflow/content specification, source-checked on 15 November 2026. Frontend implementation and playback export follow separately. The fitted model, split and evaluation remain fixed.

## Purpose and information origins

Help users review physiological changes, understand a short-term forecast, record context and access understandable information when immediate consultation is limited. Demonstrate this using terrestrial HAPP chamber records.

Keep **Research-data replay · terrestrial chamber study** visible. Use these labels consistently on the interface and summary:

| Label | Information | Origin |
| --- | --- | --- |
| Recorded measurement | Current SpO2, heart rate and respiratory rate | Released HAPP observations, already processed by the publisher |
| Calculated change | Recent differences and observed trends | Arithmetic over identified recorded readings |
| Model forecast | Predicted next-30-second mean SpO2 | Saved Ridge pipeline |
| Model-derived insight | Forecast difference, contributions and evolution | Calculations using model outputs/parameters and identified observations |
| User-entered context | Symptoms, activity, measurement concerns, notes | Demonstration input for the selected snapshot |
| Sourced guidance | Educational explanations and applicability limits | Linked FDA/NASA resources |
| Review prompt | Invitation to review an item | Authored application rule with identified evidence |
| Evaluation results | Actual MAE and participant counts | Saved experiment, in the evidence view |
| Compiled summary | Record retaining the above labels | Compilation of snapshot information and context |

Released HAPP records are not live astronaut telemetry. The publisher already forward filled missing observations; no individual imputation mask was supplied. Complete CSVs cannot establish original sensor completeness or per-reading reliability. A user-reported measurement concern is separate from dataset completeness.

## Journey

**Review measurements → explore forecasts → enter context → review relevant information → download summary.**

### Review measurements

Select a held-out test participant and elapsed replay second c. Zero is that participant's first released observation; do not invent mission dates. Show current SpO2 (%), heart rate (beats/min) and respiratory rate (breaths/min), labelled Recorded measurement.

For each signal, calculate its value at c minus its value at c-30, labelled Calculated change. SpO2 differences use percentage points. Before c=30, history is insufficient. A missing/non-finite endpoint makes that change unavailable; never substitute zero or perform additional imputation. Keep observed chart marks, text alternatives, tooltips and summary values bounded by c.

### Explore the model

Use the existing selected Ridge prediction at original issue second i. It predicts the mean of the 30 readings at i+1 through i+30 inclusive.

At cursor c, select this participant's latest forecast record with issue <= c. It is active only if its prediction is finite and c < forecast_end_s. At the forecast end, the outcome window has elapsed; hide it as an active estimate. A missing latest prediction is unavailable; do not silently revive an earlier forecast. Before first issue 59, state that forecast history is warming up.

Show the original issue time, target interval and age c-i with every active forecast insight. Between issues, never shift the target window to appear newer. Expired estimates may remain in past forecast history with their original labels.

#### Insight A: difference from the reading at issue

Label: Model-derived insight. Show recorded issue-time SpO2 r_i, predicted next-window mean p_i (Model forecast), and p_i-r_i in percentage points.

Copy: **The predicted average is X percentage points above/below the reading when this forecast was issued.** For displayed zero: **The predicted average matches the reading at issue time to the displayed precision.** If r_i is missing, the comparison is unavailable even if the forecast exists. Never compare to a later cursor reading and call that an issue-time difference.

This is a window-average comparison, not an exact second-30 value, a guaranteed direction or a clinical-event probability.

#### Insight B: what influenced this estimate

Label: Model-derived insight. Use the exact saved scaler, fitted coefficients and original ordered 19-feature vector:

```text
z_j = (x_j - training_scaler.mean_[j]) / training_scaler.scale_[j]
contribution_j = fitted_ridge.coef_[j] * z_j
forecast = fitted_ridge.intercept_ + sum(contribution_j)
```

Use the scaler's actual transform, including its saved handling of constant features. Group every feature exactly once by prefix: `spo2_`, `heart_rate_`, `respiratory_rate_`. Sum signed contributions within groups. Do not refit anything.

Show **Model reference prediction** (intercept, SpO2 %) plus three **Model contribution** values (signed percentage points). Their sum must reconstruct the saved prediction within 1e-10 percentage points at full precision. Display rounding can prevent an exact visible sum; explain that and retain full precision in exports. Missing explanation inputs make the explanation unavailable rather than fabricated.

Copy: **These values describe how the model calculated this estimate relative to its training reference. They do not establish physiological causes or prove that a signal improves prediction.** The reference is not a personal normal reading, clinical norm or persistence forecast. Correlated features limit attribution interpretation.

#### Insight C: how forecasts have evolved

Label: Model-derived insight. Show finite predictions issued during [max(0,c-60), c], inclusive, for this participant only, ordered by issue time. Points retain their separate target windows. A later issue never appears, even if the eventual browser payload contains it.

For active issue i, compare p_i with the finite prediction issued exactly at i-30. Calculate p_i-p_(i-30). Copy: **Successive 30-second mean estimates changed by X percentage points across forecasts issued 30 seconds apart.** Explain that their target windows differ. Without that exact earlier record or an active latest forecast, show **Not enough applicable forecast history for the 30-second comparison.** Do not interpolate missing records or render issued forecast history as a future physiological trajectory.

### Enter context

Label: **User-entered context · demonstration input**. Collect:

- Symptoms: `unknown` (default), `none_reported`, `reported`; optional symptom note.
- Activity/context: optional text.
- Measurement reliability: `unknown` (default), `no_concerns_reported`, `concerns_reported`; optional concern note.
- Optional responder note. All notes default empty.

Store drafts only in session memory, keyed by the exact `(participant_id, replay_time_s)` pair. New snapshots get independent defaults; returning restores only that snapshot's draft. Use copies so editing one draft cannot modify another/defaults. Refresh clears drafts. Do not copy between participants/seconds, persist to local storage or transmit notes.

Context is not matched HAPP data and never enters the predictor list, mutates observations or changes precomputed forecasts/contributions/history. A no-concerns report is not verified sensor quality; no symptoms reported does not establish health. Render notes as plain text. Summary generation does not contact medical support.

### What to review

Section explanation: **These prompts follow application rules using the evidence shown. They are not a learned medical assessment.** Display every applicable prompt in this order, without clinical urgency categories:

| Order / rule ID | Trigger | Prompt | Evidence / guidance |
| --- | --- | --- | --- |
| 1 / symptoms_reported | symptoms = reported | Symptoms reported. Review your symptoms alongside the readings. | User-entered symptoms/note; `symptoms-trends` |
| 2 / measurement_concern | reliability = concerns_reported | Measurement reliability concern recorded. | User-entered reliability/note; `measurement-quality` |
| 3 / observed_spo2_decrease | available displayed 30-second SpO2 change < 0 | Recorded SpO₂ decreased by X percentage points over 30 seconds. | Calculated change and both recorded endpoints; `symptoms-trends` |
| 4 / forecast_below_issue | available displayed active forecast difference < 0 | The model’s predicted average is X percentage points below the reading when this forecast was issued. | Model-derived difference, issue/window and recorded issue-time reading; `understand-spo2` |
| 5 / symptoms_unknown | symptoms = unknown | Symptoms have not been recorded. | User-entered status/default; focus symptom input |
| 6 / reliability_unknown | reliability = unknown | Measurement reliability has not been assessed. | User-entered status/default; focus reliability input and `measurement-quality` |
| 7 / insufficient_observed_history | c < 30 | Not enough history to describe the 30-second change. | Replay time/history availability; `symptoms-trends` |

At c>=30 with a missing endpoint, show the affected change's unavailable status/reason; do not claim insufficient elapsed history. Forecast warm-up/missing/expired statuses appear in the forecast section independently of these prompts.

For direction wording, round to one decimal place, halves away from zero, then normalize negative zero. Trigger sign comes from the displayed value; X is its non-negative magnitude. Preserve full precision for calculations. A -0.04 difference displays 0.0 and does not trigger a decrease; -0.05 displays -0.1 and does. This is display precision, not a clinical threshold. Never generate an all-clear/healthy/safe status from absent prompts, stable/rising readings or no reported symptoms.

Keep all five guidance cards accessible at every snapshot, regardless of forecast/context availability. Cards carry the Sourced guidance label, references, review date and applicability. Exact application triggers are our product decisions, not validated or endorsed agency instructions. No mission-approved clinical procedure has been supplied.

### Download a compiled summary

The eventual local text/JSON summary includes origin badge and HAPP source/license; participant and replay time; available measurements and 30-second changes; active forecast issue/age/window/method/value; issue-time reading/difference; model reference and grouped contributions; past forecast history/evolution; user context/statuses; prompts and evidence references; unknowns/unavailability reasons; and guidance references/review date.

Label it Compiled summary and retain each component's provenance. Exclude future observed outcomes, later-issued forecasts, expired estimates as active forecasts, fabricated confidence intervals, clinical urgency and treatment recommendations. Aggregate model scores stay in the evidence view. Download is local, with no transmission or medical contact.

## Guidance review

Educational content is in `../web/public/data/guidance.json`, source-checked on 15 November 2026 against [FDA Pulse Oximeter Basics](https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics), [NASA Risk of Hypoxia](https://www.nasa.gov/reference/risk-of-hypoxia/) and [NASA Distance From Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/). Source review is not clinical review or mission approval. Avoid posture-dependent terrestrial instructions, clinical cutoffs and treatment settings. Serious/worsening symptom and help information remains accessible without waiting for a forecast.

## Frontend/export acceptance scenarios

These are implementation contract cases, not claims that a frontend already exists or has been exercised.

| Case | Expected behavior |
| --- | --- |
| Cursor 0 or 29 | Available readings; 30-second changes unavailable; no forecast; unknown context; all guidance accessible |
| Cursor 30 | Changes compare exactly seconds 0 and 30; no forecast before 59 |
| Cursor 59 | First forecast targets 60 through 89; age zero; no i-30 comparison |
| Cursor 61 | Latest issue 59, age two, target still 60 through 89; difference uses reading at 59 |
| Latest forecast missing/non-finite | Unavailable; no earlier estimate silently substituted as fresh |
| Only issue 59 exists; cursor 89 | Estimate expired as active; its history point may remain |
| Missing change endpoint | Null change/reason; no zero fill or decrease prompt |
| Deltas -0.04, -0.05, 0, +0.05 | Display 0.0, -0.1, 0.0, +0.1; only the negative displayed result triggers a decrease |
| Active issue 89; earlier issue 59 exists | Evolution is p_89-p_59, with both distinct target windows identified |
| i-30 record missing | Evolution comparison unavailable; no interpolation |
| Cursor 88; payload also contains issue 89 | Issue 89 excluded from active selection and history |
| Symptoms/quality concerns reported plus both decreases | Prompts 1,2,3,4 in order, with distinct evidence origins |
| Symptoms and reliability unknown | Unknown prompts; no inferred absence of symptoms/concerns |
| Participant/snapshot changed | Independent defaults; prior draft restored only at its own key |
| Any context field edited | Measurements, forecasts, contributions and history remain unchanged |
| Stable/rising values with no concerns reported | Descriptive values, no all-clear; guidance remains accessible |
| Summary at c | No observed outcomes or forecast issues later than c; all origins/unknowns retained |

Saved-model contribution arithmetic can be verified now without fitting. Keep completed content/model checks distinct from these future browser integration checks.
