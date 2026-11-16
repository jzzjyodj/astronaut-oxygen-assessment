"""Frozen participant partitions and past-only HAPP forecasting examples."""

from __future__ import annotations

import hashlib
import io
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from oxygen_assessment.quality import audit_dataset

SEED = 42
SHUFFLE_METHOD = "numpy.random.default_rng(42).permutation(sorted_participant_ids)"
SPLIT_SIZES = {"train": 12, "validation": 4, "test": 4}
HISTORY_SECONDS = 60
HORIZON_SECONDS = 30
STRIDE_SECONDS = 5
TARGET_COLUMN = "target_mean_spo2"
SIGNALS = {"spo2": "SPO2", "heart_rate": "Heart rate", "respiratory_rate": "Respiratory rate"}
METADATA_COLUMNS = [
    "participant_id", "partition", "issue_time_s", "history_start_s",
    "history_end_s", "forecast_start_s", "forecast_end_s", TARGET_COLUMN,
]


def feature_definitions() -> dict:
    definitions = {}
    for signal, column in SIGNALS.items():
        descriptions = {
            "current": "Value at issue time t",
            "mean_60s": "Arithmetic mean of observations t-59 through t",
            "std_60s": "Population standard deviation (ddof=0) of observations t-59 through t",
            "change_10s": "Value at t minus value at t-10",
            "change_30s": "Value at t minus value at t-30",
            "slope_60s": "Ordinary least squares slope against seconds 0 through 59, with an intercept",
        }
        if signal == "spo2":
            descriptions = {"current": descriptions["current"], "mean_60s": descriptions["mean_60s"],
                            "min_60s": "Minimum of observations t-59 through t", **descriptions}
        for statistic, description in descriptions.items():
            unit = {"spo2": "%", "heart_rate": "beats/min", "respiratory_rate": "breaths/min"}[signal]
            if signal == "spo2" and statistic in {"std_60s", "change_10s", "change_30s", "slope_60s"}:
                unit = "SpO2 percentage points"
            if statistic == "slope_60s":
                unit += " per second"
            definitions[f"{signal}_{statistic}"] = {"source_column": column, "definition": description, "unit": unit}
    return definitions


FEATURE_COLUMNS = list(feature_definitions())


def resolve_split(audit: dict, manifest_path: Path) -> tuple[dict, bool]:
    """Create a split once, or validate and reuse the exact stored assignment."""
    if audit["status"] != "pass":
        raise ValueError("Data quality checks failed; no forecasting data will be prepared.")
    sources = sorted([
        {"participant_id": item["participant_id"], "relative_path": item["relative_path"],
         "row_count": item["row_count"], "sha256": item["integrity"]["sha256"]}
        for item in audit["files"]
    ], key=lambda item: item["participant_id"])
    ids = [item["participant_id"] for item in sources]
    if len(ids) != 20 or len(set(ids)) != 20:
        raise ValueError("The split requires exactly 20 unique participants.")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("schema_version") != 1 or manifest.get("seed") != SEED
                or manifest.get("shuffle_method") != SHUFFLE_METHOD):
            raise ValueError("Saved split configuration differs from the fixed split specification.")
        if manifest.get("sources") != sources:
            raise ValueError("Participant membership or source files changed; the saved split will not be reshuffled.")
        partitions = manifest.get("partitions", {})
        assigned = []
        if set(partitions) != set(SPLIT_SIZES):
            raise ValueError("Saved split must contain train, validation and test partitions.")
        for partition, size in SPLIT_SIZES.items():
            members = partitions[partition]
            if (not isinstance(members, list) or len(members) != size
                    or not all(isinstance(member, str) for member in members)):
                raise ValueError(f"Saved {partition} partition must contain {size} participant IDs.")
            assigned.extend(members)
        if len(set(assigned)) != 20 or set(assigned) != set(ids):
            raise ValueError("Saved split has duplicate, missing or unexpected participant IDs.")
        return manifest, True

    shuffled = np.random.default_rng(SEED).permutation(ids).tolist()
    partitions = {}
    start = 0
    for partition, size in SPLIT_SIZES.items():
        partitions[partition] = sorted(shuffled[start:start + size])
        start += size
    manifest = {
        "schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED, "shuffle_method": SHUFFLE_METHOD,
        "numpy_version_at_creation": np.__version__, "partitions": partitions,
        "source": audit["source"], "sources": sources,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also prevents a concurrent run from replacing the split.
    with manifest_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest, False


def make_examples(frame: pd.DataFrame, participant_id: str, partition: str) -> pd.DataFrame:
    """Use a single, prevalidated, contiguous 1 Hz participant series.

    No clock time or participant ID is a predictor. Non-finite histories and
    target windows are omitted; the full pipeline rejects failed source audits.
    """
    if partition not in SPLIT_SIZES:
        raise ValueError(f"Unknown partition: {partition}")
    issues = np.arange(HISTORY_SECONDS - 1, len(frame) - HORIZON_SECONDS, STRIDE_SECONDS, dtype=int)
    columns = METADATA_COLUMNS + FEATURE_COLUMNS
    if not len(issues):
        return pd.DataFrame(columns=columns)

    histories = {}
    valid = np.ones(len(issues), dtype=bool)
    for signal, column in SIGNALS.items():
        values = pd.to_numeric(frame[column], errors="raise").to_numpy(dtype=float)
        histories[signal] = np.lib.stride_tricks.sliding_window_view(values, HISTORY_SECONDS)[issues - 59]
        valid &= np.isfinite(histories[signal]).all(axis=1)
    spo2 = pd.to_numeric(frame["SPO2"], errors="raise").to_numpy(dtype=float)
    targets = np.lib.stride_tricks.sliding_window_view(spo2, HORIZON_SECONDS)[issues + 1]
    valid &= np.isfinite(targets).all(axis=1)
    issues = issues[valid]
    result = {
        "participant_id": np.repeat(str(participant_id), len(issues)),
        "partition": np.repeat(partition, len(issues)),
        "issue_time_s": issues, "history_start_s": issues - 59, "history_end_s": issues,
        "forecast_start_s": issues + 1, "forecast_end_s": issues + HORIZON_SECONDS,
        TARGET_COLUMN: targets[valid].mean(axis=1),
    }
    seconds = np.arange(HISTORY_SECONDS, dtype=float)
    centered_seconds = seconds - seconds.mean()
    slope_denominator = np.square(centered_seconds).sum()
    for signal, history in histories.items():
        history = history[valid]
        result[f"{signal}_current"] = history[:, -1]
        result[f"{signal}_mean_60s"] = history.mean(axis=1)
        if signal == "spo2":
            result[f"{signal}_min_60s"] = history.min(axis=1)
        result[f"{signal}_std_60s"] = history.std(axis=1, ddof=0)
        result[f"{signal}_change_10s"] = history[:, -1] - history[:, -11]
        result[f"{signal}_change_30s"] = history[:, -1] - history[:, -31]
        result[f"{signal}_slope_60s"] = history @ centered_seconds / slope_denominator
    return pd.DataFrame(result, columns=columns)


def prepare_forecasting_data(raw_dir: Path, artifacts_dir: Path, output_dir: Path,
                             metadata_path: Path | None = None) -> dict:
    """Audit, freeze/reuse the split, then export unscaled feature tables."""
    metadata = None
    if metadata_path is not None and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    audit = audit_dataset(raw_dir, metadata)
    if audit["status"] != "pass":
        raise ValueError("Data quality checks failed:\n" + "\n".join(audit["issues"]))
    split, reused = resolve_split(audit, artifacts_dir / "split_manifest.json")
    sources = {item["participant_id"]: item for item in split["sources"]}
    tables = {}
    participant_counts = {}
    for partition, members in split["partitions"].items():
        examples = []
        for participant_id in sorted(members):
            source = sources[participant_id]
            content = (raw_dir / source["relative_path"]).read_bytes()
            if hashlib.sha256(content).hexdigest() != source["sha256"]:
                raise ValueError(f"Source changed after auditing: {participant_id}")
            frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
            participant_examples = make_examples(frame, participant_id, partition)
            expected = max(0, (len(frame) - 90) // STRIDE_SECONDS + 1)
            if len(participant_examples) != expected:
                raise ValueError(f"Unexpected number of complete windows for {participant_id}.")
            participant_counts[participant_id] = len(participant_examples)
            examples.append(participant_examples)
        table = pd.concat(examples, ignore_index=True)
        if table.empty:
            raise ValueError(f"No eligible forecasting examples in {partition}.")
        if not np.isfinite(table[FEATURE_COLUMNS + [TARGET_COLUMN]].to_numpy(dtype=float)).all():
            raise ValueError(f"Non-finite computed values in {partition}.")
        tables[partition] = table

    output_dir.mkdir(parents=True, exist_ok=True)
    exports = {}
    for partition, table in tables.items():
        path = output_dir / f"{partition}.csv"
        table.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")
        exports[partition] = {"filename": path.name, "participant_count": len(split["partitions"][partition]),
                              "example_count": len(table), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {
        "schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "split_manifest": "split_manifest.json",
        "split_manifest_sha256": hashlib.sha256((artifacts_dir / "split_manifest.json").read_bytes()).hexdigest(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "settings": {"history_seconds": HISTORY_SECONDS, "horizon_seconds": HORIZON_SECONDS,
                     "stride_seconds": STRIDE_SECONDS, "first_issue_time_s": 59,
                     "history_interval": "t-59 through t, inclusive",
                     "target_interval": "t+1 through t+30, inclusive",
                     "std_ddof": 0, "scaling_applied": False},
        "feature_columns": FEATURE_COLUMNS, "feature_definitions": feature_definitions(),
        "metadata_columns": METADATA_COLUMNS, "target_column": TARGET_COLUMN,
        "target_definition": "Mean SpO2 (%) over the 30 observations after issue time",
        "exports": exports, "examples_by_participant": dict(sorted(participant_counts.items())),
        "total_examples": sum(len(table) for table in tables.values()),
        "quality_check": {"status": audit["status"], "checked_at_utc": audit["generated_at_utc"],
                          "summary": audit["summary"]},
        "limitations": [audit["limitations"][0], audit["limitations"][1],
                        "Overlapping windows are correlated; all examples for a participant remain in one partition.",
                        "Only features and targets were prepared; no model fitting, evaluation or predictions were performed."],
    }
    (artifacts_dir / "forecast_preparation.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return {"manifest": manifest, "split_reused": reused}
