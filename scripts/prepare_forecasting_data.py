"""Prepare participant-separated HAPP features and targets without fitting models."""

import argparse
import sys
from pathlib import Path

from oxygen_assessment.forecasting import prepare_forecasting_data

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--artifacts-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed" / "forecasting")
    args = parser.parse_args()
    try:
        result = prepare_forecasting_data(args.raw_dir, args.artifacts_dir, args.output_dir,
                                          args.raw_dir / "happ_metadata.json")
    except (ValueError, OSError) as error:
        print(f"Preparation stopped: {error}", file=sys.stderr)
        return 1
    manifest = result["manifest"]
    print("Current source data quality: pass")
    print("Participant split: " + ("reused" if result["split_reused"] else "created and frozen"))
    for partition, export in manifest["exports"].items():
        print(f"{partition}: {export['participant_count']} participants, {export['example_count']:,} examples")
    print(f"Total: {manifest['total_examples']:,} examples; {len(manifest['feature_columns'])} unscaled features")
    print(f"CSV datasets: {args.output_dir}")
    print(f"Manifests: {args.artifacts_dir}")
    print("No models fitted or evaluated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
