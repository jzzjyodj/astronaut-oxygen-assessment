"""Inspect released HAPP CSV files without altering any observations."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_COLUMNS = [
    "Altitude", "Time", "SPO2", "Heart rate", "Respiratory rate",
    "O2", "N2", "CO2", "other",
]
NUMERIC_COLUMNS = [column for column in EXPECTED_COLUMNS if column != "Time"]
SOURCE_URL = "https://doi.org/10.6084/m9.figshare.29947679"
METADATA_URL = "https://api.figshare.com/v2/articles/29947679"
PAPER_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC12886808/"


def inspect_file(path: Path, publisher_file: dict | None = None) -> dict:
    """Profile one participant file; timestamps must increase at one second."""
    content = path.read_bytes()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    frame = frame.replace(r"^\s*$", np.nan, regex=True)
    issues = []
    if header != EXPECTED_COLUMNS:
        issues.append("Columns or column order differ from the HAPP schema.")
    if frame.empty:
        issues.append("No observations.")

    missing = {column: int(count) for column, count in frame.isna().sum().items()}
    if sum(missing.values()):
        issues.append("Missing cells in the released CSV.")
    duplicate_rows = int(frame.duplicated().sum())
    if duplicate_rows:
        issues.append("Duplicate complete rows.")

    stats = {}
    for column in NUMERIC_COLUMNS:
        if column not in frame:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        non_numeric = int((frame[column].notna() & values.isna()).sum())
        non_finite = int((values.notna() & ~np.isfinite(values)).sum())
        finite = values[np.isfinite(values)]
        out_of_bounds = int((finite < 0).sum())
        if column in {"SPO2", "O2", "N2", "CO2", "other"}:
            out_of_bounds += int((finite > 100).sum())
        stats[column] = {
            "minimum": float(finite.min()) if len(finite) else None,
            "maximum": float(finite.max()) if len(finite) else None,
            "mean": float(finite.mean()) if len(finite) else None,
            "non_numeric_cells": non_numeric,
            "non_finite_cells": non_finite,
            "outside_mathematical_bounds": out_of_bounds,
            "zero_values": int((finite == 0).sum()),
        }
        if non_numeric or non_finite or out_of_bounds:
            issues.append(f"Invalid numeric values in {column}.")

    time_profile = None
    if "Time" in frame:
        text = frame["Time"].str.strip()
        correct_shape = text.str.fullmatch(r"\d{1,2}:\d{2}:\d{2}", na=False)
        parsed = pd.to_datetime(text.where(correct_shape), format="%H:%M:%S", errors="coerce")
        invalid = int(parsed.isna().sum())
        seconds = parsed.dt.hour * 3600 + parsed.dt.minute * 60 + parsed.dt.second
        steps = seconds.diff()
        duplicates = int(seconds.dropna().duplicated().sum())
        backward = int((steps < 0).sum())
        gaps = int((steps > 1).sum())
        non_unit_steps = int((steps.notna() & (steps != 1)).sum())
        elapsed = None
        if len(seconds) and invalid == 0 and backward == 0:
            elapsed = float(seconds.iloc[-1] - seconds.iloc[0])
        time_profile = {
            "first_clock_time": str(text.iloc[0]) if len(text) else None,
            "last_clock_time": str(text.iloc[-1]) if len(text) else None,
            "invalid_time_cells": invalid,
            "duplicate_timestamp_rows": duplicates,
            "backward_steps": backward,
            "gaps_over_one_second": gaps,
            "non_unit_steps": non_unit_steps,
            "elapsed_seconds": elapsed,
        }
        if invalid or duplicates or backward or gaps or non_unit_steps:
            issues.append("Invalid, repeated, backward or non-contiguous clock times.")

    actual_md5 = hashlib.md5(content).hexdigest()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    expected_md5 = publisher_file.get("computed_md5") or publisher_file.get("supplied_md5") if publisher_file else None
    expected_size = publisher_file.get("size") if publisher_file else None
    md5_match = actual_md5.lower() == str(expected_md5).lower() if expected_md5 else None
    size_match = len(content) == expected_size if expected_size is not None else None
    if md5_match is False or size_match is False:
        issues.append("File differs from the publisher checksum or size.")

    return {
        "participant_id": path.stem,
        "filename": path.name,
        "row_count": int(len(frame)),
        "column_count": len(frame.columns),
        "columns": header,
        "missing_cells_by_column": missing,
        "duplicate_complete_rows": duplicate_rows,
        "numeric": stats,
        "time": time_profile,
        "integrity": {
            "size_bytes": len(content), "md5": actual_md5, "sha256": actual_sha256,
            "publisher_md5": expected_md5, "publisher_md5_matches": md5_match,
            "publisher_size_bytes": expected_size, "publisher_size_matches": size_match,
        },
        "issues": issues,
    }


def audit_dataset(raw_dir: Path, metadata: dict | None = None) -> dict:
    """Audit all local participant CSVs and reconcile the publisher manifest."""
    paths = sorted(raw_dir.rglob("*.csv"))
    publisher_files = {
        item["name"]: item for item in (metadata or {}).get("files", [])
        if item["name"].lower().endswith(".csv")
    }
    profiles = []
    issues = []
    for path in paths:
        try:
            profile = inspect_file(path, publisher_files.get(path.name))
            profile["relative_path"] = path.relative_to(raw_dir).as_posix()
            profiles.append(profile)
        except (ValueError, OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
            issues.append(f"Cannot inspect {path.name}: {error}")
    names = [path.name for path in paths]
    if not paths:
        issues.append("No CSV files found.")
    if len(names) != len(set(names)):
        issues.append("Repeated participant filenames in different directories.")
    missing_files = sorted(set(publisher_files) - set(names))
    unexpected_files = sorted(set(names) - set(publisher_files)) if publisher_files else []
    if missing_files or unexpected_files:
        issues.append("Local file coverage differs from the publisher CSV manifest.")
    if len(paths) != 20:
        issues.append(f"Expected 20 HAPP participant files; found {len(paths)}.")

    for profile in profiles:
        issues.extend(f"{profile['filename']}: {issue}" for issue in profile["issues"])
    totals = {
        "csv_files_found": len(paths),
        "csv_files_profiled": len(profiles),
        "total_rows": sum(item["row_count"] for item in profiles),
        "total_bytes": sum(item["integrity"]["size_bytes"] for item in profiles),
        "missing_cells": sum(sum(item["missing_cells_by_column"].values()) for item in profiles),
        "duplicate_complete_rows": sum(item["duplicate_complete_rows"] for item in profiles),
        "non_numeric_cells": sum(value["non_numeric_cells"] for item in profiles for value in item["numeric"].values()),
        "non_finite_cells": sum(value["non_finite_cells"] for item in profiles for value in item["numeric"].values()),
        "outside_mathematical_bounds": sum(value["outside_mathematical_bounds"] for item in profiles for value in item["numeric"].values()),
        "publisher_md5_matches": sum(item["integrity"]["publisher_md5_matches"] is True for item in profiles),
    }
    for key in ["invalid_time_cells", "duplicate_timestamp_rows", "backward_steps", "gaps_over_one_second"]:
        totals[key] = sum((item["time"] or {}).get(key, 0) for item in profiles)
    totals["recording_hours_at_assumed_1hz"] = totals["total_rows"] / 3600
    ranges = {}
    for column in NUMERIC_COLUMNS:
        values = [item["numeric"][column] for item in profiles if column in item["numeric"] and item["numeric"][column]["minimum"] is not None]
        ranges[column] = {
            "minimum": min((value["minimum"] for value in values), default=None),
            "maximum": max((value["maximum"] for value in values), default=None),
        }

    warnings = [
        "The paper reports forward filling before release; no per-observation imputation mask is available. Zero missing cells does not establish complete original sensor measurements.",
        "These are healthy-volunteer terrestrial chamber records, not astronaut telemetry or adjudicated clinical events.",
        "Time is clock time without mission dates. Backward clock steps, including possible midnight rollover, require explicit review rather than automatic correction.",
        "Range checks use mathematical bounds only, not clinical alert thresholds. No observations were removed or imputed.",
        "No features, participant partitions or model evaluations were created by this audit.",
    ]
    if not metadata:
        warnings.append("Publisher metadata unavailable: source checksums and participant coverage were not independently verified.")
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not issues else "needs_review",
        "grain": "One observation per participant per second in each released CSV.",
        "source": {"title": (metadata or {}).get("title", "HAPP"), "url": SOURCE_URL,
                   "metadata_url": METADATA_URL, "paper_url": PAPER_URL,
                   "version": (metadata or {}).get("version"), "license": (metadata or {}).get("license"),
                   "publisher_metadata_available": metadata is not None},
        "summary": totals, "ranges": ranges,
        "missing_publisher_files": missing_files, "unexpected_local_files": unexpected_files,
        "issues": issues, "limitations": warnings, "files": profiles,
    }


def save_outputs(audit: dict, artifacts_dir: Path) -> None:
    """Save aggregate profiles and provenance, never observation-level records."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "data_quality.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    manifest = {
        "generated_at_utc": audit["generated_at_utc"], "source": audit["source"],
        "processing_note": audit["limitations"][0],
        "files": [{"filename": item["filename"], "participant_id": item["participant_id"],
                   "row_count": item["row_count"], **item["integrity"]} for item in audit["files"]],
    }
    (artifacts_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def format_summary(audit: dict) -> str:
    summary = audit["summary"]
    lines = [
        f"Data quality: {audit['status']}",
        f"Participants/files: {summary['csv_files_profiled']}/{summary['csv_files_found']}",
        f"Observations: {summary['total_rows']:,}",
        f"Recording hours (rows / 3600 at 1 Hz): {summary['recording_hours_at_assumed_1hz']:.2f}",
        f"Missing cells: {summary['missing_cells']}",
        f"Duplicate timestamps: {summary['duplicate_timestamp_rows']}",
        f"Backward steps / gaps over 1 second: {summary['backward_steps']} / {summary['gaps_over_one_second']}",
        f"Invalid numeric cells (non-numeric / non-finite / outside bounds): {summary['non_numeric_cells']} / {summary['non_finite_cells']} / {summary['outside_mathematical_bounds']}",
        f"Publisher checksum matches: {summary['publisher_md5_matches']}/{summary['csv_files_found']}",
    ]
    for column in ["SPO2", "Heart rate", "Respiratory rate"]:
        lines.append(f"{column} observed range: {audit['ranges'][column]['minimum']} to {audit['ranges'][column]['maximum']}")
    lines.extend(f"ISSUE: {issue}" for issue in audit["issues"])
    lines.extend(f"NOTE: {note}" for note in audit["limitations"])
    return "\n".join(lines) + "\n"
