# Implementation plan

This is a working summary of the supplied handover. The handover's instructions and proposed settings are project context; implementation should follow the user's current request and actual environment.

## Deliverables

- Public historical research-data replay with assessment and evidence views.
- Reproducible offline data preparation, evaluation and frontend export.
- Seven-slide deck featuring the working prototype and actual results.

## Suggested build order

1. **Deployment foundation:** inspect available hosting, initialize the frontend in `web/`, and publish a minimal page. Confirm active submission requirements and deadline.
2. **Data acquisition:** download the HAPP CSV files using the publisher manifest. Preserve originals, check checksums, and record provenance and source processing limitations.
3. **Analysis:** save a participant-separated 12/4/4 train/validation/test split. Use past-only 60-second features to predict the next 30-second mean SpO2, with examples every five seconds. Compare persistence and Ridge; add small boosting only if time permits. Select on validation, then evaluate the frozen choice on test participants.
4. **Integration:** export computed manifests, metrics and held-out playback data using `data-contract.md`.
5. **Assessment UI:** implement measurements, replay, trend and forecast display, educational cards, user context and a downloadable summary.
6. **Evidence and verification:** display real results, baseline comparison, sources and limitations. Check units, nulls, history/forecast boundaries, keyboard use and public access.
7. **Presentation:** create the seven-slide deck in `reports/slides/`; use real screenshots from `reports/figures/`. Verify links and finish submission.

## Checks that matter

- Participant IDs cannot cross partitions; feature calculations cannot access future observations.
- Data provenance and the historical replay label stay visible.
- The forecast is a next-window mean, with its issue time and target interval shown correctly.
- Missing values remain explicit; no invented evaluation metrics or clinical labels appear.
- Context inputs are identified as user-entered and do not change precomputed predictions.
- Summary downloads work; the chart has a text alternative.
- Both the public demo and presentation open without a login.

Autoplay, additional plots, extra models and extensive tuning are optional. Prioritize the complete demo, honest evaluation and required presentation.
