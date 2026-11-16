"""Boundary, leakage, partition integrity and reproducibility checks."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from oxygen_assessment.forecasting import (
    FEATURE_COLUMNS, METADATA_COLUMNS, TARGET_COLUMN, make_examples,
    prepare_forecasting_data, resolve_split,
)


def sequence(length=100):
    seconds = np.arange(length, dtype=float)
    return pd.DataFrame({"SPO2": seconds, "Heart rate": 100 + 2 * seconds,
                         "Respiratory rate": 10 + 0.1 * seconds})


def fake_audit():
    return {"status": "pass", "source": {}, "files": [
        {"participant_id": f"p{i:02}", "relative_path": f"p{i:02}.csv", "row_count": 100,
         "integrity": {"sha256": hashlib.sha256(str(i).encode()).hexdigest()}}
        for i in range(20)
    ]}


def test_hand_calculated_features_and_target_boundaries():
    examples = make_examples(sequence(), "sample", "train")
    first = examples.iloc[0]
    assert len(FEATURE_COLUMNS) == 19
    assert set(FEATURE_COLUMNS).isdisjoint(METADATA_COLUMNS)
    assert list(examples.columns) == METADATA_COLUMNS + FEATURE_COLUMNS
    assert first[["issue_time_s", "history_start_s", "history_end_s", "forecast_start_s", "forecast_end_s"]].tolist() == [59, 0, 59, 60, 89]
    assert first["spo2_current"] == 59
    assert first["spo2_mean_60s"] == 29.5
    assert first["spo2_min_60s"] == 0
    assert first["spo2_std_60s"] == pytest.approx(np.sqrt((60 ** 2 - 1) / 12))
    assert first["spo2_change_10s"] == 10
    assert first["spo2_change_30s"] == 30
    assert first["spo2_slope_60s"] == pytest.approx(1)
    assert first["heart_rate_slope_60s"] == pytest.approx(2)
    assert first["respiratory_rate_slope_60s"] == pytest.approx(0.1)
    assert first[TARGET_COLUMN] == 74.5
    assert examples["issue_time_s"].tolist() == [59, 64, 69]
    assert examples.iloc[-1]["forecast_end_s"] == 99


def test_future_mutations_change_label_but_not_features():
    original = sequence()
    changed = original.copy()
    changed.loc[60:, ["SPO2", "Heart rate", "Respiratory rate"]] += 1000
    before = make_examples(original, "sample", "test").iloc[0]
    after = make_examples(changed, "sample", "test").iloc[0]
    np.testing.assert_array_equal(before[FEATURE_COLUMNS], after[FEATURE_COLUMNS])
    assert after[TARGET_COLUMN] == before[TARGET_COLUMN] + 1000


def test_exact_minimum_length_and_incomplete_windows():
    assert make_examples(sequence(89), "short", "validation").empty
    assert len(make_examples(sequence(90), "complete", "validation")) == 1
    frame = sequence(100)
    frame.loc[0, "Heart rate"] = np.nan
    assert make_examples(frame, "partial", "train")["issue_time_s"].tolist() == [64, 69]
    frame = sequence(100)
    frame.loc[99, "SPO2"] = np.nan
    assert make_examples(frame, "partial", "train")["issue_time_s"].tolist() == [59, 64]


def test_split_is_frozen_and_rejects_changed_sources_or_members(tmp_path):
    path = tmp_path / "split_manifest.json"
    audit = fake_audit()
    manifest, reused = resolve_split(audit, path)
    original_bytes = path.read_bytes()
    assert reused is False
    assert {key: len(value) for key, value in manifest["partitions"].items()} == {"train": 12, "validation": 4, "test": 4}
    assigned = sum(manifest["partitions"].values(), [])
    assert len(assigned) == len(set(assigned)) == 20
    # Fix expected membership independently of the split implementation.
    assert manifest["partitions"]["test"] == ["p01", "p08", "p13", "p17"]
    reused_manifest, reused = resolve_split(audit, path)
    assert reused is True and reused_manifest == manifest
    assert path.read_bytes() == original_bytes
    audit["files"][0]["integrity"]["sha256"] = "changed"
    with pytest.raises(ValueError, match="source files changed"):
        resolve_split(audit, path)
    audit = fake_audit()
    audit["files"][0]["participant_id"] = "new_participant"
    with pytest.raises(ValueError, match="membership or source files changed"):
        resolve_split(audit, path)
    assert path.read_bytes() == original_bytes


def test_invalid_saved_split_and_failed_audit_are_rejected(tmp_path):
    path = tmp_path / "split_manifest.json"
    audit = fake_audit()
    manifest, _ = resolve_split(audit, path)
    manifest["partitions"]["test"][0] = manifest["partitions"]["train"][0]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate, missing or unexpected"):
        resolve_split(audit, path)
    audit["status"] = "needs_review"
    with pytest.raises(ValueError, match="quality checks failed"):
        resolve_split(audit, tmp_path / "absent.json")
    assert not (tmp_path / "absent.json").exists()


def write_test_dataset(raw_dir):
    raw_dir.mkdir()
    for i in range(20):
        frame = sequence(100)
        frame["SPO2"] = 80 + i / 2 + np.arange(100) / 100
        frame["Heart rate"] = 60 + i
        frame["Respiratory rate"] = 12 + i / 10
        clock_times = pd.date_range("2000-01-01 09:59:20", periods=100, freq="s")
        frame.insert(0, "Time", clock_times.strftime("%H:%M:%S"))
        frame.insert(0, "Altitude", 5000)
        frame = frame.assign(O2=40, N2=55, CO2=3, other=2)
        frame.to_csv(raw_dir / f"p{i:02}.csv", index=False)


def test_full_preparation_keeps_participants_separate_and_repeats_exactly(tmp_path):
    raw_dir = tmp_path / "raw"
    artifacts = tmp_path / "artifacts"
    outputs = tmp_path / "processed"
    write_test_dataset(raw_dir)
    raw_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in raw_dir.glob("*.csv")}
    first = prepare_forecasting_data(raw_dir, artifacts, outputs)
    split_bytes = (artifacts / "split_manifest.json").read_bytes()
    export_bytes = {path.name: path.read_bytes() for path in outputs.glob("*.csv")}
    assert first["manifest"]["total_examples"] == 60
    seen = set()
    for partition, expected_participants in {"train": 12, "validation": 4, "test": 4}.items():
        table = pd.read_csv(outputs / f"{partition}.csv", dtype={"participant_id": str})
        ids = set(table["participant_id"])
        assert len(ids) == expected_participants
        assert not (ids & seen)
        seen |= ids
        assert table["partition"].eq(partition).all()
        for participant_id, participant in table.groupby("participant_id"):
            assert participant["issue_time_s"].tolist() == [59, 64, 69]
            i = int(participant_id[1:])
            assert participant["heart_rate_current"].eq(60 + i).all()
            np.testing.assert_allclose(participant["spo2_current"], 80 + i / 2 + participant["issue_time_s"] / 100)
    assert len(seen) == 20
    second = prepare_forecasting_data(raw_dir, artifacts, outputs)
    assert second["split_reused"] is True
    assert (artifacts / "split_manifest.json").read_bytes() == split_bytes
    assert {path.name: path.read_bytes() for path in outputs.glob("*.csv")} == export_bytes
    assert {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in raw_dir.glob("*.csv")} == raw_hashes
    # A valid but changed source must stop preparation before replacing outputs.
    path = raw_dir / "p00.csv"
    path.write_bytes(path.read_bytes().replace(b"5000", b"5001", 1))
    with pytest.raises(ValueError, match="source files changed"):
        prepare_forecasting_data(raw_dir, artifacts, outputs)
    assert {path.name: path.read_bytes() for path in outputs.glob("*.csv")} == export_bytes
