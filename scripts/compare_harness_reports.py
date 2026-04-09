#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FASTAPI_ROOT = ROOT / "services" / "fastapi"
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

from final_ai.harness import compare_harness_reports, load_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline and candidate harness reports.")
    parser.add_argument("--baseline", required=True, help="Baseline JSON report path.")
    parser.add_argument("--candidate", required=True, help="Candidate JSON report path.")
    parser.add_argument("--report", default="", help="Optional JSON comparison output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline_report = load_report(args.baseline)
    candidate_report = load_report(args.candidate)
    comparison = compare_harness_reports(baseline_report, candidate_report)

    print("Harness Report Comparison")
    summary = comparison["summary"]
    print(
        "baseline_failed_cases={baseline_failed_cases} candidate_failed_cases={candidate_failed_cases} "
        "delta={failed_case_delta}".format(**summary)
    )
    print(f"status_regressions={len(comparison['status_regressions'])}")
    print(f"status_improvements={len(comparison['status_improvements'])}")

    if comparison["status_regressions"]:
        print("status_regression_cases=" + ", ".join(comparison["status_regressions"]))
    if comparison["average_metric_regressions"]:
        print("average_metric_regressions=" + ", ".join(comparison["average_metric_regressions"]))

    if args.report:
        Path(args.report).write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report={args.report}")

    return 0 if comparison["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
