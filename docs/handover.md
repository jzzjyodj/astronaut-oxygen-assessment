# Astronaut oxygen assessment prototype — Codex handover

Updated 15 November 2026. This document consolidates the current decisions from planning Steps 1–4 and supersedes the earlier sleep-first and general-collapse concepts. It is a build brief, not evidence of an implemented or clinically validated product.

## 1. Read this first

- User: JZ, a data scientist, working with one teammate. About **3–4 hours remain for the project**. Do not plan a research-grade system or a long discovery phase.
- Latest judging information supplied by the user: **judges will assess the seven-slide deck and the final public prototype URL**. Prioritize a clear working demo, an accessible interface, a reliable public link and a concise story. Technical details need only a brief, accurate explanation in the deck and an evidence tab.
- Working scope: **a visual oxygen/cardiorespiratory assessment tool**, using HAPP research observations to demonstrate trends, a short-horizon forecast, measurement explanations, contextual notes and a consultation summary.
- Main numerical dataset: HAPP, described below. It contains real observations from healthy volunteers in a terrestrial hypobaric chamber. It is **not astronaut telemetry**.
- Proposed analytics: persistence baseline, Ridge regression, and a small gradient-boosted regressor if time permits. No model has been fitted in this conversation. Winning method and metrics must come from actual evaluation.
- Prefer a **static web frontend with offline Python analysis and precomputed predictions**. This makes a public URL easier to deliver than a live inference backend. Label the experience as historical research-data replay.
- No approved product name. Use a descriptive title such as “Oxygen Assessment” until JZ chooses a name. “AstroGuard” was an earlier unapproved suggestion.
- User requested this file to start building in a fresh Codex conversation. When asked to implement, execute the prioritized plan; do not restart dataset discovery or ask about routine implementation choices. Adapt to the actual repository/deployment capabilities available.

## 2. Problem, risk and value

NASA Space Apps 2026 challenge: **Create Health Monitoring Software for Astronauts on Space Missions**.

Official objectives: a visual tool that helps astronauts assess their own health, explains how to obtain and understand health indicators, and provides supported guidance. A narrow coherent prototype is acceptable; the challenge does not require all listed indicators, all five hazards, every emergency, a chatbot or a predictive model.

Working problem statement:

> Crew members operating with limited immediate ground support need a simple way to understand changes in oxygen saturation and related measurements, record symptoms/context, and access understandable assessment information.

Hazard/risk mapping:

- **Hostile/closed environment → hypoxia risk**: NASA discusses monitoring health in reduced-pressure exploration environments.
- **Distance from Earth → need for local information and organized consultation records**. This is an operational constraint, not a diagnosis or cause of every deterioration.
- HAPP chamber altitude and breathing-mask gas measurements are experimental context. They must not be presented as measured spacecraft cabin conditions or as the NASA mission atmosphere. NASA currently describes the relevant exploration hypoxia risk as relatively low; do not exaggerate its frequency.

User decision supported: “What has changed, how trustworthy/complete is the information, what should I review next, and what should I include in a medical consultation?”

Differentiation from a wearable is the assessment workflow: understandable trends, contextual notes, source-linked explanations and an organized summary. A model or graph alone does not establish superiority over an Apple Watch. No wearable connection is implemented or assumed.

Learning goals to preserve: statistical reasoning, applied ML, model evaluation, decision analytics, product thinking and data product development. Keep the experiment small but honest; a baseline outperforming ML is a valid finding.

## 3. What the prototype should look like

Build **two tabs/pages**, with a polished main view and compact supporting evidence.

### A. Assessment — main demo

1. **Header and provenance**
   - Descriptive title, short purpose, and an explicit badge: “Research-data replay · terrestrial chamber study”.
   - Select a participant and move a replay slider through elapsed study time. Default to an actual held-out participant and a visually useful real segment; do not choose the participant to inflate evaluation results.
   - A slider and previous/next controls are sufficient. Autoplay is optional.
2. **Three readable measurement cards**
   - SpO2 (%), heart rate (beats/min), respiratory rate (breaths/min).
   - Show actual current readings and recent numerical changes, with explicit units. Unknown/unavailable values must not display as zero.
   - Prefer descriptive change information to medical traffic lights. Do not label a person “healthy” because an alert is absent.
3. **One primary oxygen trend chart**
   - Recent measured SpO2 over a useful history window, current replay position and the separately marked forecast.
   - The forecast target is a scalar mean over the next 30 seconds. Render a point or clearly labeled horizontal forecast segment. Do not invent a full predicted trajectory or confidence band.
   - Hide future observed data at the current replay position. Provide a textual trend summary and visible data origin.
4. **“Understand this reading” expandable cards**
   - What oxygen saturation means; recording/measurement quality; why NASA studies hypoxia; source/applicability links.
   - Keep clinical limits, diagnosis and treatment assertions out unless appropriate sources have actually been verified. Reviewed educational material can be bundled locally.
5. **Brief assessment/context form and summary**
   - Symptom report: none reported / symptoms reported / unknown, with a short optional note. Default unknown rather than “no symptoms”.
   - Activity/context, perceived measurement reliability and an optional responder note.
   - Context is user-entered or explicitly scripted; it is not a real matched field from HAPP and does not alter the precomputed model forecast.
   - “Generate summary” produces a readable local summary: provenance, participant ID, replay time, observed readings, recent change, separately identified forecast/model, symptoms/context and unknowns.
   - Download as plain text or JSON. No real transmission or medical contact is implemented.

### B. Evidence — compact credibility view

- Dataset origin, 20 participants, about 44 hours, study license and source link.
- Actual validation/test metrics and the persistence comparison. State the split and the number of held-out participants.
- Concise limitations, five research references, NASA resources and AI/tool acknowledgments as appropriate.
- If a model fails or is dropped, report the actual available method and results. Do not show invented scores or imply all planned checks ran.

Accessibility: large controls, readable type, high contrast, meaningful labels, keyboard navigation, visible focus, units, text alongside any color and a text alternative to the chart. Avoid dense technical terminology in the main assessment workflow.

## 4. Data acquisition — direct links and verified facts

**HAPP: High-Altitude Pilot Physiological Monitoring Dataset: Respiratory Performance and SpO2 Analysis**

- Dataset landing: https://doi.org/10.6084/m9.figshare.29947679
- Public metadata and complete download manifest: https://api.figshare.com/v2/articles/29947679
- Dataset version 1, published 23 October 2025; license **CC BY 4.0**.
- Example CSV 0609b.csv: https://ndownloader.figshare.com/files/57303830
- Example CSV 0620b.csv: https://ndownloader.figshare.com/files/57303842
- Associated paper published **26 January 2026**: https://doi.org/10.1038/s41597-025-06508-1
- Full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC12886808/

To obtain all observations: fetch the public metadata JSON; select entries in `files` with `.csv` names; download each returned `download_url`; retain filename, size, source/version/license and checksum. Do not guess file identifiers. Validate MD5 against the metadata if feasible. Do not execute supplied analysis scripts without inspection.

Verified in this conversation by downloading and auditing all 20 CSVs:

- 20 usable participant files; **158,580 rows**, about **44.05 hours** at 1 Hz.
- Total original CSV bytes: **6,771,096**. All 20 publisher MD5 values matched.
- Columns: `Altitude`, `Time`, `SPO2`, `Heart rate`, `Respiratory rate`, `O2`, `N2`, `CO2`, `other`.
- Participants: healthy male volunteers, ages 18–40, exposed to controlled hypobaric/oxygen conditions. Not actual astronauts.
- No missing cells, duplicate within-file timestamps, backward jumps or gaps greater than one second were found in the released CSVs. **The paper states that forward filling was already performed**; do not claim originally complete raw observations. No individual imputation mask was identified.
- SpO2 observed range 70–100. Low observations require review; the range is not a clinical alert policy. No adjudicated clinical emergencies or treatment outcomes were identified.
- `Time` is clock time. Build relative elapsed seconds per participant; do not invent mission dates or a continuous multiday astronaut record.
- Preserve original observations. Any missingness/communications demonstration must be a separate, explicitly labeled synthetic scenario.

Earlier local files existed under `feasibility_round2/happ/`, but paths from this chat are not portable. This handover includes public links so a fresh Codex environment can acquire the data independently. If download is blocked, explain the precise missing input and keep any temporary demo data explicitly synthetic; do not claim real-data evaluation.

## 5. Fast, defensible analytical implementation

These are **proposed engineering settings**, not literature-established optimal values or clinical response times. The deadline permits adjusting implementation details, provided the task and evaluation remain honest.

### Target and features

- At time t, use only the previous 60 seconds, including the current observation.
- Predict **mean SpO2 over t+1 through t+30 seconds**. This is a next-window mean, not the reading exactly 30 seconds later, a hypoxia diagnosis or a probability of collapse.
- Create an example every 5 seconds; discard windows without complete required history and future target.
- Start with about 15–20 simple features: SpO2 current value, mean/minimum/standard deviation, recent 10-/30-second changes and slope; recent HR and RR levels, variability and slopes.
- Do not compute HRV from once-per-second HR; no beat-to-beat intervals are supplied.
- Exclude participant ID and raw clock time from predictors. Do not use future SpO2, future oxygen adjustments or any feature calculated with future/centered windows.
- Keep altitude and mask gases as optional study-context displays. Do not add them to the core model unless their availability and relevance to the intended prediction are explicitly justified.

### Simplified evaluation for this 3–4 hour build

The earlier proposal was grouped nested cross-validation. **For this deadline, use one fixed participant-separated train/validation/test split instead.** This reduces work while preserving the essential evaluation boundary.

- Sort the 20 participant identifiers, shuffle with a fixed seed such as 42, and save a manifest: **12 train / 4 validation / 4 test participants**.
- Split participants before building model datasets; all windows from a participant remain in that partition.
- Fit transformations on training participants only. Validation selects the method; test participants remain untouched until final evaluation. Do not choose the winner by test results.
- No extensive hyperparameter search or nested CV is required for the demo. Do not claim that these were performed.
- Fit: (1) persistence, predicting current SpO2; (2) Ridge regression with training-only scaling; (3) a small shallow histogram gradient boosting regressor if time permits. Use conservative fixed settings. Do not use a random row-level internal early-stopping split; disable that feature or provide a group-safe validation strategy.
- Select by mean validation MAE with equal weight per participant; prefer the simpler method when differences are small. The selected method can be fitted on train+validation after selection, with the choice frozen before testing. Report actual steps taken.
- Report final test MAE in **SpO2 percentage points**, RMSE, per-participant errors and comparison against persistence. Add a simple falling-period slice where actual next-window mean is lower than the current reading, with its definition and support count disclosed. This is a measurement slice, not a clinical event label.
- If time permits, compare SpO2-only features with SpO2+HR+RR on validation. This is secondary to finishing the product.
- Four test participants support a limited proof of concept. Do not describe the result as robust population, clinical, spaceflight or prospective validation.

### Minimum analytical output

One reproducible Python command should download/cache data, prepare eligible windows, fit/evaluate the small candidate set and export frontend assets.

Export real, computed artifacts only:

- Participant split manifest and source/license metadata.
- Metrics for the methods actually evaluated, with validation selection clearly identified.
- A few held-out playback series with elapsed time, actual SpO2/HR/RR and eligible precomputed forecasts.
- Predictions contain their issue time and forecast-window endpoints; missing predictions are null, including the initial warm-up period.

Do not spend the whole build optimizing models. If boosting is not ready quickly, ship persistence and Ridge comparison. If ML does not improve on persistence, use the baseline in the demo and report that result honestly. No clinical thresholds or diagnostic accuracy can be established from this dataset.

## 6. Architecture and suggested code contract

Recommended fast path:

- Python: pandas, NumPy, scikit-learn for reproducible offline analysis.
- Frontend: React/Vite or the simplest suitable existing web stack, using a lightweight available chart library or SVG. Use the repository's existing conventions if present.
- Host: whichever existing public static deployment capability is available. Establish a working public skeleton early. No live Python inference server, database, login, API key, LLM or wearable integration is needed.
- Precomputed predictions are acceptable for an interactive historical-data replay. Label them accurately. Do not pretend moving a slider runs a live medical model.
- Ship a small number of held-out participants/segments in the browser; keep full training data in the analysis workflow. No need to send every experimental gas column to the frontend.
- Bundle required references/assets for local use after installation. A hosted page is not automatically an offline application/PWA; only claim offline behavior actually tested.

Suggested structure, adaptable to the actual environment:

- `analysis/prepare_and_evaluate.py`
- `data/raw/` (cached original source files)
- `artifacts/split_manifest.json`, `artifacts/metrics.json`
- `public/data/demo.json`, `public/data/guidance.json`
- frontend source, `README.md`, dependency files

Minimum frontend data contract:

- `metadata`: source title/URL/version/license, origin label, target definition, method and split description.
- `participants`: ID, held-out status, measured series of elapsed seconds and the three indicators.
- `forecasts`: participant, issue time, forecast start/end, predicted next-window mean and method. Null when unavailable.
- `evaluation`: actual metrics, evaluated participant counts and baseline comparison; absent until computed.
- `guidance`: short title/text, source URL, source date/version where available and applicability note.
- `assessment`: user-entered symptom/context fields, clearly separated from measured research data.

If both teammates are available: JZ can own the analysis/export; the teammate can build UI/deck against this contract. Agree on the export shape immediately and cross-check integration. Do not assume equal technical skills or that another agent/repository already exists.

## 7. Guidance content and clinical boundaries

Use short reviewed educational cards, not a generated treatment chatbot.

Useful initial sources:

- NASA hazards: https://www.nasa.gov/hrp/hazards/
- NASA risks: https://www.nasa.gov/hrp/risks/
- NASA ongoing research: https://www.nasa.gov/hrp/ongoing-hrp-research/
- NASA hypoxia: https://www.nasa.gov/reference/risk-of-hypoxia/
- NASA distance from Earth: https://www.nasa.gov/hrp/hazard-distance-from-earth/
- NASA ExMC clinical decision-support concept: https://ntrs.nasa.gov/citations/20220017856
- FDA pulse-oximeter basics: https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics
- FDA pulse-oximeter overview/limitations: https://www.fda.gov/medical-devices/products-and-medical-procedures/pulse-oximeters

Safe content scope for the prototype: SpO2 estimates oxygen saturation; record reading/time/source; follow the actual instrument instructions; consider symptoms and trends alongside a reading; motion, circulation, skin pigmentation and other factors can affect measurement accuracy. FDA material is general terrestrial device information, not a microgravity procedure. Do not copy posture-dependent instructions into a spacecraft workflow without checking applicability.

No complete current NASA mission-approved treatment protocol has been verified. Do not present this demo as NASA-approved, prescribe oxygen settings, classify every collapse, or advise waiting for a forecast before accessing urgent assistance. An optional urgent-reference link must be independent of analytics and clearly identify its coverage.

Manual context is a demonstration input, not observed HAPP clinical data. Synthetic missing-reading or communication scenarios test software behavior only. Keep original research data, artificial perturbations and clinical claims distinct.

## 8. Five academic studies informing the method (2021–2026)

All five selected studies are within the requested period. They inform this design; none clinically validates it for astronauts.

| Study | Relevant evidence | Application and limit |
|---|---|---|
| Jia, Yang & Zhao (2026), High-Altitude Pilot Physiological Monitoring Dataset: Respiratory Performance and SpO2 Analysis. https://doi.org/10.1038/s41597-025-06508-1 | HAPP collection, physiological/context variables, 20 usable volunteers, source processing. | Grounds the actual inputs and limitations. Dataset study, not an established predictive algorithm. |
| Park et al. (2023), Machine learning-based prediction of intraoperative hypoxemia for pediatric patients. https://doi.org/10.1371/journal.pone.0282303 | One-minute-ahead physiological prediction; GBM outperformed LSTM/transformer in that study; patient-separated and later temporal evaluation. | Supports testing a small boosted-tree candidate. Different pediatric anesthesia population/inputs; do not transfer its thresholds or accuracy. Its labels included ongoing hypoxemia, so reported performance is not pure first-onset early-warning performance. |
| Wang et al. (2022), Predicting Adverse Events During Six-Minute Walk Test Using Continuous Physiological Signals. https://doi.org/10.3389/fphys.2022.887954 | Oxygen-change/HR features useful; logistic regression performed close to LightGBM in the reported cohort. | Supports temporal features and a simple comparator. Different clinical population, richer sensors and adverse-event labels. |
| Grinsztajn, Oyallon & Varoquaux (2022), Why do tree-based models still outperform deep learning on typical tabular data? https://papers.neurips.cc/paper_files/paper/2022/hash/0378c7692da36807bdec87ab043cdadc-Abstract-Datasets_and_Benchmarks.html | Strong tree-ensemble performance across 45 tabular benchmarks. | Reason to benchmark trees before deep learning; not proof of superiority on HAPP or regression forecasting. |
| Kapoor & Narayanan (2023), Leakage and the reproducibility crisis in machine-learning-based science. https://doi.org/10.1016/j.patter.2023.100804 | Taxonomy and examples of leakage causing overoptimistic scientific results. | Justifies group separation, causal feature windows, training-only preprocessing and bounded performance claims. |

Chosen design family: descriptive monitoring + supervised continuous forecasting + source-grounded assessment workflow. The model winner remains empirical. LLMs and deep learning are not required. Deliberate oxygen interventions confound natural progression; no causal dose recommendation is supported.

## 9. Three-hour execution plan, with a fourth-hour buffer

The **public URL and seven-slide deck are required deliverables**, not optional finishing touches.

| Elapsed time | Priority/output |
|---|---|
| 0–15 min | Inspect environment, create minimal frontend and establish a public URL/deployment path. Agree on the data contract. |
| 15–55 min | Acquire/cache HAPP, make fixed participant split, run persistence/Ridge and a small boosting comparison if quick, export actual results and demo segments. |
| 55–115 min | Complete main assessment UI, replay/chart, explanations, context form and downloadable summary. Integrate the real exports. |
| 115–135 min | Add evidence view, check provenance/units/nulls/forecast boundaries, test main flow and public link in a signed-out/private browser. |
| 135–180 min | Finish the seven-slide deck, capture the real prototype, verify both public links and complete required submission fields. |
| Optional fourth hour | Improve clarity/accessibility, fix actual failures, refine deck and modestly strengthen evaluation. Avoid new features. |

If deployment is blocked, resolve that early and simplify the stack. Do not spend the last minutes discovering that judges cannot open the app. Inspect actual available hosting/auth capabilities; do not assume credentials or a repository.

Cut first: autoplay, extra participants/plots, extra models, extensive tuning, animations and elaborate styling. Preserve data honesty, the baseline comparison, readable assessment flow, a working URL and the deck.

## 10. Seven-slide story

User says judges assess the deck and prototype URL. Keep details brief and let the demo show the experience.

1. **Problem and crew decision** — understandable onboard health assessment when immediate expert support is limited.
2. **NASA relevance** — hostile/closed environment, hypoxia and distance from Earth; bounded oxygen-monitoring scope.
3. **Prototype walkthrough** — measurements → trend/forecast → explanation/context → consultation summary; readable screenshot.
4. **Data and method** — HAPP, 20 people/about 44 hours, historical chamber observations, 60-second history/30-second mean forecast, baseline comparison. Mention precomputed replay openly.
5. **Evidence and actual results** — a small baseline/model table, participant-separated holdout and principal limitation. No invented numbers.
6. **Value and boundaries** — understandable guidance, accessible design and organized handoff; prototype rather than validated clinical care. Note future mission-data/expert validation.
7. **Try it / sources / team** — prominent clickable public prototype URL, source/code link if available, concise NASA/HAPP/academic acknowledgments and honest AI contribution disclosure.

Check readability at presentation size. Do not turn the deck into an algorithm report. Recheck required submission fields and the guide before final submission:

- Challenge: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=details
- Resources: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=resources
- Submission guide: https://www.spaceappschallenge.org/resources/project-submission-guide/
- Judging guide: https://www.spaceappschallenge.org/resources/judging-awards-guide/

Previously recorded event deadline: 15 November 2026, 11:59 PM Ottawa local time; the user's latest instruction is a 3–4 hour work budget. Recheck the active event deadline and submit with a buffer. Ensure public links need no login/permission and click the actual submission action rather than only saving a draft. The user's specific deck-and-URL judging instruction takes priority over earlier packaging suggestions; do not spend time on a separate video unless required by the active form.

## 11. Minimum completion checks

- Original data acquisition succeeds with clear provenance and license; study records are not relabeled as astronauts.
- One held-out real-data replay works end to end.
- Metrics are produced by executed analysis; participant IDs never cross partitions; predictions use available history only.
- SpO2 mean forecast is displayed accurately with units and time window; future observations are hidden at the decision point.
- Unknowns remain explicit, context stays separate from measured data, and summary download works.
- Sources are visible; no unsupported diagnosis, treatment promise or invented clinical threshold is shown.
- Main workflow is keyboard usable and readable; chart has a text summary.
- Public prototype and seven-slide deck open without sign-in and match the behavior actually built.

## 12. Earlier options — retained context, not current build scope

- General emergency/collapse assistance was explored because the challenge video uses a collapse example. Unresponsiveness does not establish cardiac arrest. Complete current public NASA mission treatment procedures were not verified. Do not expand this MVP into a general emergency clinician.
- VTaC: https://physionet.org/content/vtac/1.1/ — 5,037 expert-labeled terrestrial ICU VT alarms. Stronger supervised alarm classification option, but a different product/signal-processing task. Do not merge with HAPP or add for this build.
- NASA sleep: https://nlsp.nasa.gov/search/data/details/e26501eb-7d7a-5012-8c8e-c5bdb3eecaf6?dataType=DATASETS — three ground-analogue participants, 69 rows each, 190 complete participant-days. Useful for sleep review, not acute-event labels. Earlier team Word brief and feasibility ZIP reflect that older scope.
- Inspiration4 OSD-569/575: https://osdr.nasa.gov/bio/repo/data/studies/OSD-569 and https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 — real pre/postflight laboratory observations from four crew, sparse visits, not acute telemetry. Not part of current app.
- Wearable stress/exercise: https://physionet.org/content/wearable-device-dataset/1.0.1/ — reserve behavioral-monitoring direction, not required.
- BIDMC: https://physionet.org/content/bidmc/1.0.0/ — reserve respiratory-estimation direction, not required.
- OpenOximetry currently requires registered access and a signed agreement; no access was obtained. Do not silently substitute it.

## 13. Start in Codex

Suggested user kickoff after attaching this file:

> Read handover.md and build the prioritized 3–4 hour prototype. Judges assess the seven-slide deck and public prototype URL, so establish deployment early. Use HAPP data with a small participant-separated persistence/Ridge/boosting comparison as time permits, and export actual predictions for an accessible interactive historical-data replay. Keep the assessment/context/summary flow simple. Do not restart broad research, invent metrics, or claim clinical validation. Tell me what you built, actual evaluation results, remaining limits and the public URL; help finish the seven-slide deck.

Current status at handover: Steps 1–4 planning/data screening/literature research completed; HAPP downloaded/audited in the prior workspace; **no application, trained model, evaluation scores, repository, deployment or slide deck has yet been created**. Steps 5–6 should proceed as an iterative design/build loop; adapt Steps 7–8 to the implementation and the user's judging priorities.
