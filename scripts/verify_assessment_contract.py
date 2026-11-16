"""Verify saved-model maths/content and reference cases; no frontend or fitting.

The replay/context cases below are a reference walkthrough of the specification,
not tests of a browser application. The report states that boundary explicitly.
"""

import copy
import hashlib
import json
import pickle
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_active(records, cursor):
    past = [record for record in records if record["issue"] <= cursor]
    if not past:
        return None
    latest = max(past, key=lambda record: record["issue"])
    if latest["prediction"] is None or not np.isfinite(latest["prediction"]) or cursor >= latest["end"]:
        return None
    return latest


def reference_history(records, cursor):
    return [record for record in records
            if max(0, cursor - 60) <= record["issue"] <= cursor
            and record["prediction"] is not None and np.isfinite(record["prediction"])]


def reference_evolution(records, cursor):
    active = reference_active(records, cursor)
    if active is None:
        return None
    previous = next((record for record in records if record["issue"] == active["issue"] - 30), None)
    if previous is None or previous["prediction"] is None or not np.isfinite(previous["prediction"]):
        return None
    return active["prediction"] - previous["prediction"]


def main():
    artifacts = ROOT / "artifacts"
    protected = [artifacts / name for name in [
        "models/ridge_pipeline.pkl", "split_manifest.json", "metrics.json",
        "model_selection.json", "forecast_preparation.json",
    ]]
    before = {str(path.relative_to(ROOT)): digest(path) for path in protected}
    selection = json.loads((artifacts / "model_selection.json").read_text())
    metrics = json.loads((artifacts / "metrics.json").read_text())
    split = json.loads((artifacts / "split_manifest.json").read_text())
    preparation = json.loads((artifacts / "forecast_preparation.json").read_text())
    model_path = artifacts / "models/ridge_pipeline.pkl"
    assert digest(model_path) == selection["ridge_model"]["sha256"]
    assert digest(artifacts / "model_selection.json") == metrics["selection_record"]["sha256"]
    assert digest(artifacts / "split_manifest.json") == preparation["split_manifest_sha256"]
    pipeline = pickle.loads(model_path.read_bytes())
    columns = selection["feature_columns"]
    assert len(columns) == 19 and columns == preparation["feature_columns"]
    assert not any("symptom" in column or "context" in column or "reliability" in column for column in columns)
    features_path = ROOT / "data/processed/forecasting/test.csv"
    predictions_path = ROOT / "data/processed/predictions/test.csv"
    assert digest(features_path) == selection["input_checksums"]["datasets"]["test"]
    assert digest(predictions_path) == metrics["prediction_exports"]["test"]["sha256"]
    features = pd.read_csv(features_path, dtype={"participant_id": str})
    predictions = pd.read_csv(predictions_path, dtype={"participant_id": str})
    pd.testing.assert_frame_equal(features[["participant_id", "issue_time_s"]], predictions[["participant_id", "issue_time_s"]])
    coefficients = pipeline["ridge"].coef_
    individual = pipeline["scaler"].transform(features[columns]) * coefficients
    groups = {}
    covered = np.zeros(len(columns), dtype=int)
    for name in ["spo2", "heart_rate", "respiratory_rate"]:
        mask = np.array([column.startswith(name + "_") for column in columns])
        covered += mask
        groups[name] = individual[:, mask].sum(axis=1)
    assert (covered == 1).all()
    reconstructed = float(pipeline["ridge"].intercept_) + sum(groups.values())
    maximum_error = float(np.max(np.abs(reconstructed - predictions["selected_prediction"].to_numpy())))
    assert maximum_error <= 1e-10
    source_paths = {item["participant_id"]: item["relative_path"] for item in split["sources"]}
    differences_checked = 0
    for participant, participant_predictions in predictions.groupby("participant_id", sort=True):
        raw = pd.read_csv(ROOT / "data/raw" / source_paths[participant])
        issues = participant_predictions["issue_time_s"].to_numpy(dtype=int)
        recorded_at_issue = raw["SPO2"].iloc[issues].to_numpy()
        np.testing.assert_allclose(recorded_at_issue, participant_predictions["spo2_current"], atol=1e-12)
        expected_difference = participant_predictions["selected_prediction"].to_numpy() - recorded_at_issue
        stored_issue_difference = participant_predictions["selected_prediction"] - participant_predictions["spo2_current"]
        np.testing.assert_allclose(expected_difference, stored_issue_difference, atol=1e-12)
        differences_checked += len(issues)

    guidance = json.loads((ROOT / "web/public/data/guidance.json").read_text(encoding="utf-8"))
    assert guidance["schema_version"] == 1 and guidance["available_independently_of_forecast"] is True
    sources = {source["id"]: source for source in guidance["sources"]}
    cards = {card["id"]: card for card in guidance["cards"]}
    assert len(sources) == 3 and len(cards) == 5
    assert set(cards) == {"understand-spo2", "measurement-quality", "symptoms-trends", "spaceflight-context", "consultation-help"}
    for source in sources.values():
        assert source["url"].startswith("https://")
        assert source["reviewed_on"] == guidance["reviewed_on"] and source["applicability"]
    for card in cards.values():
        assert card["provenance"] == "sourced_guidance" and card["body"] and card["applicability"]
        assert card["reviewed_on"] == guidance["reviewed_on"]
        assert card["source_ids"] and set(card["source_ids"]) <= set(sources)
    workflow = (ROOT / "docs/assessment-workflow.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs/data-contract.md").read_text(encoding="utf-8")
    for identifier in ["recorded_measurement", "calculated_change", "model_forecast", "model_derived_insight", "user_entered_context", "sourced_guidance", "review_prompt", "evaluation_result", "compiled_summary"]:
        assert identifier in contract
    for identifier in cards:
        assert identifier in workflow or identifier in contract

    # Hypothetical records used only to walk through the documented time rules.
    records = [{"issue": i, "end": i + 30, "prediction": 95 + (i - 59) / 100} for i in range(59, 95, 5)]
    assert reference_active(records, 0) is None and reference_active(records, 58) is None
    assert reference_active(records, 61)["issue"] == 59
    assert reference_active(records, 61)["end"] == 89
    assert 61 - reference_active(records, 61)["issue"] == 2
    assert reference_active(records[:1], 89) is None
    assert all(record["issue"] <= 88 for record in reference_history(records, 88))
    assert not any(record["issue"] == 89 for record in reference_history(records, 88))
    assert reference_evolution(records, 59) is None
    assert abs(reference_evolution(records, 89) - 0.3) < 1e-12
    assert reference_evolution([record for record in records if record["issue"] != 59], 89) is None
    unavailable = copy.deepcopy(records[:2])
    unavailable[-1]["prediction"] = None
    assert reference_active(unavailable, 65) is None
    rounded = [float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) or 0.0
               for value in [-0.04, -0.05, 0, 0.05]]
    assert rounded == [0.0, -0.1, 0.0, 0.1]
    defaults = {"symptoms_status": "unknown", "measurement_reliability": "unknown", "symptom_note": ""}
    drafts = {}
    first_key = json.dumps(["example-a", 59])
    drafts[first_key] = copy.deepcopy(defaults)
    drafts[first_key]["symptoms_status"] = "reported"
    for key in [json.dumps(["example-a", 60]), json.dumps(["example-b", 59])]:
        drafts[key] = copy.deepcopy(defaults)
        assert drafts[key]["symptoms_status"] == "unknown"
    assert drafts[first_key]["symptoms_status"] == "reported" and defaults["symptoms_status"] == "unknown"
    after = {str(path.relative_to(ROOT)): digest(path) for path in protected}
    assert before == after
    report = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass", "stage": "workflow/content specification; frontend and playback export pending",
        "saved_test_forecasts_checked": len(predictions),
        "maximum_contribution_reconstruction_error_percentage_points": maximum_error,
        "issue_time_reading_comparisons_checked": differences_checked,
        "guidance_cards": len(cards), "guidance_sources": len(sources),
        "guidance_reference_integrity": "pass; source content was separately reviewed against the cited pages",
        "reference_contract_scenarios": "warm-up, issue-age/window anchoring, expiry, future exclusion, missing forecast/history, rounding and isolated default/draft examples passed",
        "browser_integration_checks": "Not run: no frontend is implemented. The specification includes acceptance cases for prompts, missing observed history, context isolation, model invariance and summaries.",
        "preserved_artifact_sha256": after,
        "model_fitting_or_selection_performed": False,
    }
    (artifacts / "assessment_contract_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
