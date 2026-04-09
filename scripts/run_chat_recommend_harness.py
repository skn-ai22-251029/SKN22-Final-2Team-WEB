#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FASTAPI_ROOT = ROOT / "services" / "fastapi"
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

from final_ai.harness import (  # noqa: E402
    build_state_report,
    load_state_cases,
    run_state_case,
    score_state_result,
    write_json_report,
)


DEFAULT_CASES = [
    ROOT / "services/fastapi/final_ai/tests/fixtures/chat_state_cases.jsonl",
]
DEFAULT_REPORT_DIR = ROOT / "output" / "harness-runs" / "state"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chat state acquisition harness cases.")
    parser.add_argument(
        "--cases",
        nargs="*",
        default=[str(path) for path in DEFAULT_CASES],
        help="JSONL files containing chat state harness cases.",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Optional JSON report output path. If omitted, a timestamped report is written under output/harness-runs/state.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Optional case_id filter. Can be passed multiple times.",
    )
    return parser.parse_args()


def resolve_report_path(raw_path: str) -> Path:
    if raw_path:
        return Path(raw_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_REPORT_DIR / f"chat_state_harness_{timestamp}.json"


def filter_cases(cases, case_ids: list[str]):
    if not case_ids:
        return cases
    requested = set(case_ids)
    return [case for case in cases if case.case_id in requested]


def main() -> int:
    args = parse_args()
    cases = filter_cases(load_state_cases(*args.cases), args.case_id)
    results = [run_state_case(case) for case in cases]
    scores = [score_state_result(result) for result in results]
    report = build_state_report(results, scores)
    report_path = resolve_report_path(args.report)

    print("Chat State Harness")
    print(f"cases={report['summary']['total_cases']}")
    print(f"passed={report['summary']['passed_cases']}")
    print(f"failed={report['summary']['failed_cases']}")

    for result, score in zip(results, scores):
        status = "PASS" if score.passed else "FAIL"
        print(f"- [{status}] {result.case.case_id}")
        if result.error:
            print(f"  error={result.error}")
        if score.failures:
            print(f"  failures={'; '.join(score.failures)}")
        if score.metrics:
            metric_summary = ", ".join(f"{key}={value}" for key, value in sorted(score.metrics.items()))
            print(f"  metrics={metric_summary}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_report(report, report_path)
    print(f"report={report_path}")

    return 0 if report["summary"]["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
