"""Simple evaluation math, fitting isolation and experiment integrity."""

import json
import pickle

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import oxygen_assessment.modeling as modeling
from oxygen_assessment.forecasting import FEATURE_COLUMNS, prepare_forecasting_data
from test_forecasting import write_test_dataset


@pytest.fixture
def experiment(tmp_path):
    raw = tmp_path / "raw"
    artifacts = tmp_path / "artifacts"
    data = tmp_path / "features"
    predictions = tmp_path / "predictions"
    write_test_dataset(raw)
    prepare_forecasting_data(raw, artifacts, data)
    return data, artifacts, predictions


def update_export_checksum(data, artifacts, partition):
    path = artifacts / "forecast_preparation.json"
    preparation = json.loads(path.read_text())
    preparation["exports"][partition]["sha256"] = modeling.sha256(data / f"{partition}.csv")
    modeling.write_json(path, preparation)


def test_mae_weights_people_equally_with_unequal_window_counts():
    table = pd.DataFrame({"participant_id": ["a", "a", "a", "b"],
                          "target_mean_spo2": [90.0, 90.0, 90.0, 94.0]})
    result = modeling.participant_mae(table, np.repeat(90.0, 4))
    assert result["participant_average_mae"] == 2.0
    assert result["participants"] == [
        {"participant_id": "a", "example_count": 3, "mae": 0.0},
        {"participant_id": "b", "example_count": 1, "mae": 4.0},
    ]


def test_persistence_and_numerical_tie_selection():
    frame = pd.DataFrame({"spo2_current": [70.1, 98.9, 100.0]})
    np.testing.assert_array_equal(modeling.persistence_predictions(frame), frame["spo2_current"])
    scores = {"persistence": {"participant_average_mae": 1.0}, "ridge": {"participant_average_mae": 1.0}}
    assert modeling.select_method(scores) == "persistence"
    scores["ridge"]["participant_average_mae"] = 1.0 - 5e-13
    assert modeling.select_method(scores) == "persistence"
    scores["ridge"]["participant_average_mae"] = 0.99
    assert modeling.select_method(scores) == "ridge"


def test_training_isolation_selection_order_and_model_reload(experiment, monkeypatch):
    data, artifacts, predictions = experiment
    train = pd.read_csv(data / "train.csv")
    fits = []
    scaler_fit = StandardScaler.fit
    ridge_fit = Ridge.fit
    partition_loader = modeling.load_partition

    def checked_scaler_fit(self, x, y=None, **kwargs):
        pd.testing.assert_frame_equal(x, train[FEATURE_COLUMNS])
        fits.append(("scaler", len(x)))
        return scaler_fit(self, x, y, **kwargs)

    def checked_ridge_fit(self, x, y, **kwargs):
        assert len(x) == len(train)
        np.testing.assert_array_equal(y, train["target_mean_spo2"])
        fits.append(("ridge", len(x)))
        return ridge_fit(self, x, y, **kwargs)

    def checked_loader(partition, *args, **kwargs):
        if partition == "test" and kwargs.get("include_values", True):
            saved = json.loads((artifacts / "model_selection.json").read_text())
            assert "test" not in saved
            assert saved["selected_method"] == modeling.select_method(saved["validation"])
            assert (artifacts / "models/ridge_pipeline.pkl").exists()
        return partition_loader(partition, *args, **kwargs)

    monkeypatch.setattr(StandardScaler, "fit", checked_scaler_fit)
    monkeypatch.setattr(Ridge, "fit", checked_ridge_fit)
    monkeypatch.setattr(modeling, "load_partition", checked_loader)
    metrics = modeling.train_and_evaluate(data, artifacts, predictions)
    assert fits == [("scaler", 36), ("ridge", 36)]
    pipeline = pickle.loads((artifacts / "models/ridge_pipeline.pkl").read_bytes())
    np.testing.assert_allclose(pipeline["scaler"].mean_, train[FEATURE_COLUMNS].mean().to_numpy())
    assert pipeline["scaler"].n_samples_seen_ == 36
    test = pd.read_csv(data / "test.csv")
    saved = pd.read_csv(predictions / "test.csv")
    np.testing.assert_allclose(pipeline.predict(test[FEATURE_COLUMNS]), saved["ridge_prediction"], atol=1e-12)
    np.testing.assert_array_equal(saved["persistence_prediction"], test["spo2_current"])
    assert saved["selected_method"].eq(metrics["selected_method"]).all()
    np.testing.assert_array_equal(saved["selected_prediction"], saved[f"{metrics['selected_method']}_prediction"])
    assert metrics["test"]["persistence"]["example_count"] == 12
    selection = artifacts / "model_selection.json"
    assert metrics["selection_record"]["sha256"] == modeling.sha256(selection)


def test_test_targets_cannot_change_fit_or_validation_winner(experiment):
    data, artifacts, predictions = experiment
    first = modeling.train_and_evaluate(data, artifacts, predictions)
    model_path = artifacts / "models/ridge_pipeline.pkl"
    before = pickle.loads(model_path.read_bytes())
    frame = pd.read_csv(data / "test.csv")
    frame["target_mean_spo2"] += 4
    frame.to_csv(data / "test.csv", index=False)
    update_export_checksum(data, artifacts, "test")
    second = modeling.train_and_evaluate(data, artifacts, predictions)
    after = pickle.loads(model_path.read_bytes())
    assert first["selected_method"] == second["selected_method"]
    assert first["validation"] == second["validation"]
    np.testing.assert_array_equal(before["scaler"].mean_, after["scaler"].mean_)
    np.testing.assert_array_equal(before["ridge"].coef_, after["ridge"].coef_)
    assert before["ridge"].intercept_ == after["ridge"].intercept_
    assert first["test"] != second["test"]


@pytest.mark.parametrize("problem", ["checksum", "features", "overlap", "membership", "nonfinite"])
def test_rejects_invalid_inputs_before_fitting(experiment, monkeypatch, problem):
    data, artifacts, predictions = experiment
    prep_path = artifacts / "forecast_preparation.json"
    preparation = json.loads(prep_path.read_text())
    if problem == "checksum":
        with (data / "train.csv").open("a") as handle:
            handle.write("\n")
    elif problem == "features":
        preparation["feature_columns"] = list(reversed(FEATURE_COLUMNS))
        modeling.write_json(prep_path, preparation)
    elif problem == "overlap":
        split_path = artifacts / "split_manifest.json"
        split = json.loads(split_path.read_text())
        split["partitions"]["test"][0] = split["partitions"]["train"][0]
        modeling.write_json(split_path, split)
        preparation["split_manifest_sha256"] = modeling.sha256(split_path)
        modeling.write_json(prep_path, preparation)
    else:
        frame = pd.read_csv(data / "train.csv")
        if problem == "membership":
            frame.loc[0, "participant_id"] = "unexpected"
        else:
            frame.loc[0, "spo2_current"] = np.inf
        frame.to_csv(data / "train.csv", index=False)
        update_export_checksum(data, artifacts, "train")

    def forbidden_fit(*args, **kwargs):
        pytest.fail("Invalid inputs reached model fitting.")

    monkeypatch.setattr(StandardScaler, "fit", forbidden_fit)
    with pytest.raises(ValueError):
        modeling.train_and_evaluate(data, artifacts, predictions)
    assert not (artifacts / "model_selection.json").exists()
    assert not predictions.exists()
