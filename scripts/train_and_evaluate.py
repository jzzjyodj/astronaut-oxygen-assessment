"""Run the fixed persistence/Ridge comparison and participant holdout evaluation."""

import argparse
import sys
from pathlib import Path

from oxygen_assessment.modeling import format_metrics, train_and_evaluate

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed" / "forecasting")
    parser.add_argument("--artifacts-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--predictions-dir", type=Path, default=ROOT / "data" / "processed" / "predictions")
    args = parser.parse_args()
    try:
        metrics = train_and_evaluate(args.data_dir, args.artifacts_dir, args.predictions_dir)
    except (ValueError, OSError, KeyError) as error:
        print(f"Training/evaluation stopped: {error}", file=sys.stderr)
        return 1
    print(format_metrics(metrics), end="")
    print(f"Metrics and selection record: {args.artifacts_dir}")
    print(f"Local prediction datasets: {args.predictions_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
