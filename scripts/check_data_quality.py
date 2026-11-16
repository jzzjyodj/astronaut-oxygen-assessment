"""Run from any directory with the project's installed Python environment."""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from oxygen_assessment.quality import METADATA_URL, audit_dataset, format_summary, save_outputs

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local HAPP CSVs without modifying them.")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data" / "raw" / "happ_metadata.json")
    parser.add_argument("--artifacts-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--fetch-metadata", action="store_true", help="Fetch publisher metadata for checksum verification; no CSVs are downloaded.")
    args = parser.parse_args()
    metadata = None
    if args.fetch_metadata:
        try:
            request = urllib.request.Request(METADATA_URL, headers={"User-Agent": "OxygenAssessmentResearchPrototype/0.1"})
            with urllib.request.urlopen(request, timeout=30) as response:
                metadata = json.load(response)
            args.metadata.parent.mkdir(parents=True, exist_ok=True)
            args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        except (OSError, ValueError) as error:
            print(f"Publisher metadata fetch failed: {error}", file=sys.stderr)
    if metadata is None and args.metadata.exists():
        metadata = json.loads(args.metadata.read_text(encoding="utf-8-sig"))
    audit = audit_dataset(args.raw_dir, metadata)
    save_outputs(audit, args.artifacts_dir)
    print(format_summary(audit), end="")
    print(f"Saved audit and source manifest to {args.artifacts_dir}")
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
