"""Small synthetic fixtures exercise failures the real dataset should reject."""

import hashlib

from oxygen_assessment.quality import EXPECTED_COLUMNS, audit_dataset, inspect_file


def write_csv(tmp_path, rows, header=None):
    path = tmp_path / "sample.csv"
    header = header or EXPECTED_COLUMNS
    path.write_text(
        ",".join(header) + "\n" + "\n".join(",".join(map(str, row)) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def row(time="12:00:00", spo2="98", heart_rate="80", respiratory_rate="16"):
    return [5000, time, spo2, heart_rate, respiratory_rate, 40, 55, 3, 2]


def test_contiguous_seconds_and_publisher_integrity(tmp_path):
    path = write_csv(tmp_path, [row(), row("12:00:01"), row("12:00:02")])
    publisher = {"computed_md5": hashlib.md5(path.read_bytes()).hexdigest(), "size": path.stat().st_size}
    result = inspect_file(path, publisher)
    assert result["issues"] == []
    assert result["time"]["elapsed_seconds"] == 2
    assert result["integrity"]["publisher_md5_matches"] is True
    assert inspect_file(path, {"computed_md5": "0" * 32})["integrity"]["publisher_md5_matches"] is False


def test_duplicates_gaps_backward_steps_and_invalid_clock(tmp_path):
    path = write_csv(tmp_path, [row(), row(), row("12:00:03"), row("11:59:59"), row("25:00:00")])
    result = inspect_file(path)
    assert result["time"]["duplicate_timestamp_rows"] == 1
    assert result["time"]["gaps_over_one_second"] == 1
    assert result["time"]["backward_steps"] == 1
    assert result["time"]["invalid_time_cells"] == 1
    assert result["time"]["elapsed_seconds"] is None


def test_single_digit_hour_and_hour_boundary(tmp_path):
    path = write_csv(tmp_path, [row("9:59:58"), row("9:59:59"), row("10:00:00")])
    result = inspect_file(path)
    assert result["issues"] == []
    assert result["time"]["invalid_time_cells"] == 0
    assert result["time"]["non_unit_steps"] == 0
    assert result["time"]["elapsed_seconds"] == 2


def test_missing_non_numeric_infinite_and_impossible_values(tmp_path):
    path = write_csv(tmp_path, [row(spo2="101", heart_rate="text", respiratory_rate="-1"), row("12:00:01", spo2="", heart_rate="inf")])
    result = inspect_file(path)
    assert result["missing_cells_by_column"]["SPO2"] == 1
    assert result["numeric"]["SPO2"]["outside_mathematical_bounds"] == 1
    assert result["numeric"]["Heart rate"]["non_numeric_cells"] == 1
    assert result["numeric"]["Heart rate"]["non_finite_cells"] == 1
    assert result["numeric"]["Respiratory rate"]["outside_mathematical_bounds"] == 1
    assert result["issues"]


def test_schema_change_and_manifest_coverage(tmp_path):
    path = write_csv(tmp_path, [row()], header=["unexpected"] + EXPECTED_COLUMNS[1:])
    assert inspect_file(path)["columns"][0] == "unexpected"
    metadata = {"files": [{"name": "missing.csv"}]}
    result = audit_dataset(tmp_path, metadata)
    assert result["status"] == "needs_review"
    assert result["missing_publisher_files"] == ["missing.csv"]
    assert result["unexpected_local_files"] == ["sample.csv"]
