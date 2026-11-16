"""One fixed persistence/Ridge experiment with participant-average MAE."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import pickle
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from oxygen_assessment.forecasting import FEATURE_COLUMNS, METADATA_COLUMNS, SPLIT_SIZES, TARGET_COLUMN

TIE_TOLERANCE = 1e-12
METHOD_CONFIGURATION = {
    "persistence": {"prediction": "spo2_current"},
    "ridge": {"scaler": "StandardScaler", "with_mean": True, "with_std": True,
              "alpha": 1.0, "solver": "svd", "fit_intercept": True},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_manifests(artifacts_dir: Path) -> tuple[dict, dict]:
    split_path = artifacts_dir / "split_manifest.json"
    preparation = json.loads((artifacts_dir / "forecast_preparation.json").read_text(encoding="utf-8"))
    split = json.loads(split_path.read_text(encoding="utf-8"))
    if preparation.get("split_manifest_sha256") != sha256(split_path):
        raise ValueError("Split manifest checksum differs from feature preparation.")
    if (preparation.get("schema_version") != 1 or split.get("schema_version") != 1
            or preparation.get("feature_columns") != FEATURE_COLUMNS
            or preparation.get("metadata_columns") != METADATA_COLUMNS
            or preparation.get("target_column") != TARGET_COLUMN
            or preparation.get("settings", {}).get("scaling_applied") is not False):
        raise ValueError("Prepared feature columns, target or schema do not match the experiment.")
    settings = preparation["settings"]
    if any(settings.get(key) != value for key, value in {
        "history_seconds": 60, "horizon_seconds": 30, "stride_seconds": 5, "first_issue_time_s": 59,
    }.items()):
        raise ValueError("Forecast window settings differ from the prepared experiment.")
    partitions = split.get("partitions", {})
    if set(partitions) != set(SPLIT_SIZES) or set(preparation.get("exports", {})) != set(SPLIT_SIZES):
        raise ValueError("Expected train, validation and test partitions.")
    assigned = []
    for name, size in SPLIT_SIZES.items():
        ids = partitions[name]
        if (not isinstance(ids, list) or len(ids) != size
                or not all(isinstance(item, str) for item in ids)):
            raise ValueError(f"Expected {size} participant IDs in {name}.")
        assigned.extend(ids)
        if preparation["exports"][name].get("participant_count") != size:
            raise ValueError(f"Prepared participant count differs in {name}.")
    if len(set(assigned)) != 20:
        raise ValueError("Participant overlap or duplicates across partitions.")
    if set(assigned) != {item["participant_id"] for item in split["sources"]}:
        raise ValueError("Participant membership differs from the frozen sources.")
    return preparation, split


def load_partition(partition: str, data_dir: Path, preparation: dict, split: dict,
                   *, include_values: bool = True) -> pd.DataFrame:
    """Check bytes/schema first; the preflight test read parses metadata only."""
    export = preparation["exports"][partition]
    if export["filename"] != f"{partition}.csv":
        raise ValueError(f"Unexpected prepared filename for {partition}.")
    content = (data_dir / export["filename"]).read_bytes()
    if hashlib.sha256(content).hexdigest() != export["sha256"]:
        raise ValueError(f"Prepared {partition} dataset checksum differs from its manifest.")
    header = next(csv.reader(io.StringIO(content.decode("utf-8-sig"))), [])
    if header != METADATA_COLUMNS + FEATURE_COLUMNS:
        raise ValueError(f"Unexpected feature/metadata columns in {partition}.")
    # Test bytes may be hashed before selection, but test targets are not parsed.
    usecols = None if include_values else [column for column in METADATA_COLUMNS if column != TARGET_COLUMN]
    table = pd.read_csv(io.BytesIO(content), usecols=usecols, dtype={"participant_id": str})
    if len(table) != export["example_count"] or table.empty:
        raise ValueError(f"Unexpected example count in {partition}.")
    if set(table["participant_id"]) != set(split["partitions"][partition]) or not table["partition"].eq(partition).all():
        raise ValueError(f"Participant membership or partition labels differ in {partition}.")
    if table.duplicated(["participant_id", "issue_time_s"]).any():
        raise ValueError(f"Duplicate participant/issue-time examples in {partition}.")
    for participant_id, group in table.groupby("participant_id", sort=True):
        if len(group) != preparation["examples_by_participant"][participant_id]:
            raise ValueError(f"Unexpected example count for {participant_id}.")
        issue_times = group["issue_time_s"].to_numpy()
        if not np.array_equal(issue_times, 59 + 5 * np.arange(len(group))):
            raise ValueError(f"Issue times are not the expected five-second sequence for {participant_id}.")
    for column, offset in {"history_start_s": -59, "history_end_s": 0,
                           "forecast_start_s": 1, "forecast_end_s": 30}.items():
        if not table[column].eq(table["issue_time_s"] + offset).all():
            raise ValueError(f"Incorrect {column} boundaries in {partition}.")
    if include_values and not np.isfinite(table[FEATURE_COLUMNS + [TARGET_COLUMN]].to_numpy(dtype=float)).all():
        raise ValueError(f"Non-finite features or targets in {partition}.")
    return table


def persistence_predictions(table: pd.DataFrame) -> np.ndarray:
    return table["spo2_current"].to_numpy(dtype=float, copy=True)


def participant_mae(table: pd.DataFrame, predictions: np.ndarray) -> dict:
    """Give each participant equal weight regardless of their window count."""
    predictions = np.asarray(predictions, dtype=float)
    actual = table[TARGET_COLUMN].to_numpy(dtype=float)
    if predictions.shape != actual.shape or not np.isfinite(predictions).all() or not np.isfinite(actual).all():
        raise ValueError("Predictions and targets must be finite, aligned one-dimensional arrays.")
    if not len(table):
        raise ValueError("Cannot evaluate an empty partition.")
    errors = pd.DataFrame({"participant_id": table["participant_id"].to_numpy(),
                           "absolute_error": np.abs(actual - predictions)})
    participants = [
        {"participant_id": str(participant_id), "example_count": len(group),
         "mae": float(group["absolute_error"].mean())}
        for participant_id, group in errors.groupby("participant_id", sort=True)
    ]
    return {"participant_average_mae": float(np.mean([item["mae"] for item in participants])),
            "participant_count": len(participants), "example_count": len(table), "participants": participants}


def evaluate_partition(table: pd.DataFrame, predictions: dict) -> dict:
    scores = {method: participant_mae(table, values) for method, values in predictions.items()}
    return {**scores, "ridge_mae_improvement": scores["persistence"]["participant_average_mae"] - scores["ridge"]["participant_average_mae"]}


def select_method(validation: dict) -> str:
    baseline = validation["persistence"]["participant_average_mae"]
    ridge = validation["ridge"]["participant_average_mae"]
    return "ridge" if ridge < baseline - TIE_TOLERANCE else "persistence"


def save_predictions(table: pd.DataFrame, predictions: dict, selected_method: str, path: Path) -> dict:
    output = table[METADATA_COLUMNS + ["spo2_current"]].copy()
    for method, values in predictions.items():
        output[f"{method}_prediction"] = values
    output["selected_method"] = selected_method
    output["selected_prediction"] = predictions[selected_method]
    path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")
    return {"filename": path.name, "example_count": len(output), "sha256": sha256(path)}


def train_and_evaluate(data_dir: Path, artifacts_dir: Path, predictions_dir: Path) -> dict:
    preparation, split = load_manifests(artifacts_dir)
    train = load_partition("train", data_dir, preparation, split)
    validation = load_partition("validation", data_dir, preparation, split)
    load_partition("test", data_dir, preparation, split, include_values=False)
    pipeline = Pipeline([
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ("ridge", Ridge(alpha=1.0, solver="svd", fit_intercept=True)),
    ])
    # This is the only fitting call in the experiment: 12 training participants.
    pipeline.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN])
    validation_predictions = {"persistence": persistence_predictions(validation),
                              "ridge": pipeline.predict(validation[FEATURE_COLUMNS])}
    validation_metrics = evaluate_partition(validation, validation_predictions)
    selected_method = select_method(validation_metrics)

    model_path = artifacts_dir / "models" / "ridge_pipeline.pkl"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(pickle.dumps(pipeline, protocol=5))
    environment = {"python": platform.python_version(), "numpy": np.__version__,
                   "pandas": pd.__version__, "scikit_learn": sklearn.__version__}
    selection = {
        "schema_version": 1, "selected_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_method": selected_method, "selection_based_on": "validation participant-average MAE only",
        "selection_rule": "Choose Ridge only when its validation MAE is lower by more than the numerical tie tolerance; otherwise choose persistence.",
        "tie_tolerance_percentage_points": TIE_TOLERANCE,
        "selection_stage": "Saved before test targets are loaded",
        "method_configuration": METHOD_CONFIGURATION, "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN, "target_definition": preparation["target_definition"],
        "training_participants": split["partitions"]["train"], "training_example_count": len(train),
        "fit_weighting": "Equal weight per training example; no refit on validation or test",
        "input_checksums": {
            "split_manifest_sha256": sha256(artifacts_dir / "split_manifest.json"),
            "forecast_preparation_sha256": sha256(artifacts_dir / "forecast_preparation.json"),
            "datasets": {name: item["sha256"] for name, item in preparation["exports"].items()},
        },
        "ridge_model": {"filename": "models/ridge_pipeline.pkl", "sha256": sha256(model_path)},
        "validation": validation_metrics, "environment": environment,
    }
    selection_path = artifacts_dir / "model_selection.json"
    write_json(selection_path, selection)

    # The choice and training pipeline are now fixed. Test scores cannot select a method.
    test = load_partition("test", data_dir, preparation, split)
    test_predictions = {"persistence": persistence_predictions(test),
                        "ridge": pipeline.predict(test[FEATURE_COLUMNS])}
    test_metrics = evaluate_partition(test, test_predictions)
    predictions = {
        "validation": save_predictions(validation, validation_predictions, selected_method, predictions_dir / "validation.csv"),
        "test": save_predictions(test, test_predictions, selected_method, predictions_dir / "test.csv"),
    }
    metrics = {
        "schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_method": selected_method, "units": "SpO2 percentage points",
        "aggregation": "Arithmetic mean of participant MAEs, with equal weight per participant",
        "ridge_mae_improvement_definition": "Persistence participant-average MAE minus Ridge participant-average MAE; positive favors Ridge",
        "target_definition": preparation["target_definition"],
        "validation": validation_metrics, "test": test_metrics,
        "selection_record": {"filename": selection_path.name, "sha256": sha256(selection_path)},
        "method_configuration": METHOD_CONFIGURATION, "input_checksums": selection["input_checksums"],
        "prediction_exports": predictions, "environment": environment,
        "limitations": [
            "Four test participants from a terrestrial chamber study support a limited proof of concept.",
            "Overlapping windows are correlated. This is not clinical, astronaut, prospective or external-cohort validation.",
            "Released observations were already forward filled by the publisher; an individual imputation mask is unavailable.",
            "One fixed Ridge configuration was evaluated. Predictions are raw and unclipped; no tuning, cross-validation or synthetic augmentation was performed.",
        ],
    }
    write_json(artifacts_dir / "metrics.json", metrics)
    return metrics


def format_metrics(metrics: dict) -> str:
    lines = [f"Selected method (validation only): {metrics['selected_method']}",
             "MAE units: SpO2 percentage points; participants weighted equally."]
    for partition in ("validation", "test"):
        scores = metrics[partition]
        lines.append(f"{partition}: {scores['persistence']['participant_count']} participants, {scores['persistence']['example_count']:,} examples")
        for method in ("persistence", "ridge"):
            lines.append(f"  {method} participant-average MAE: {scores[method]['participant_average_mae']:.6f}")
            for participant in scores[method]["participants"]:
                lines.append(f"    {participant['participant_id']}: MAE {participant['mae']:.6f}, n={participant['example_count']:,}")
        lines.append(f"  Ridge MAE improvement: {scores['ridge_mae_improvement']:+.6f}")
    return "\n".join(lines) + "\n"
