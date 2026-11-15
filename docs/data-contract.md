# Planned frontend export

The analysis pipeline will generate `web/public/data/demo.json`. This document defines the proposed integration contract; no exported data exists yet. Finalize field names when implementing the exporter and frontend together.

| Field | Contents |
| --- | --- |
| `metadata` | Schema version, dataset title and URL, version, license, origin label, target definition, selected method and split description. |
| `participants` | Held-out participant IDs and observed series with elapsed seconds, SpO2 (%), heart rate (beats/min) and respiratory rate (breaths/min). |
| `forecasts` | Participant ID, issue time, window start/end, predicted next-window mean and method. |
| `evaluation` | Actual validation/test metrics, participant and window counts, selected method and persistence comparison. |

## Conventions

- Time values are elapsed study seconds per participant, not mission dates.
- Forecast windows cover issue time + 1 through issue time + 30 seconds.
- Warm-up periods and unavailable measurements/predictions use JSON `null`, never a fabricated zero.
- Future observed readings may be present in the playback payload but must be hidden beyond the current replay position.
- Metrics must include units, aggregation method, partition and support counts. Participant-average MAE drives validation selection.
- Educational material belongs in a separate `guidance.json`, with source URLs and applicability notes.
- User-entered symptoms/context belong to local assessment state and summary downloads. They are not HAPP observations or model predictors.
- Source and split manifests in `artifacts/` retain the full reproducibility record; browser exports contain only what the demo needs.
