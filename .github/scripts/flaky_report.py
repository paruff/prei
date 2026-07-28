#!/usr/bin/env python3
"""Detect flaky tests from a pytest --report-log JSONL file.

A test is "flaky this run" when pytest-rerunfailures had to rerun it
(outcome == "rerun" on an earlier "call" report) and the final "call"
report for the same nodeid passed. Tests that still fail after retries
are real failures, not flaky ones, and are left alone.

Modes:
  --mode report  Print a markdown summary (and append to
                 $GITHUB_STEP_SUMMARY if set). Does not touch the ledger.
  --mode write   Same summary, plus updates docs/quality/flaky_tests.json
                 and tests/.flaky_quarantine.txt. Intended to run only
                 from the single main-branch writer job.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LEDGER = Path("docs/quality/flaky_tests.json")
DEFAULT_QUARANTINE = Path("tests/.flaky_quarantine.txt")
DEFAULT_THRESHOLD = 3


def find_flaky_nodeids(report_log_path: Path) -> list[str]:
    """Return nodeids whose call reports show rerun-then-pass this run."""
    call_outcomes: dict[str, list[str]] = {}

    if not report_log_path.exists():
        return []

    with report_log_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("$report_type") != "TestReport":
                continue
            if record.get("when") != "call":
                continue
            nodeid = record.get("nodeid")
            outcome = record.get("outcome")
            if nodeid is None or outcome is None:
                continue
            call_outcomes.setdefault(nodeid, []).append(outcome)

    flaky = []
    for nodeid, outcomes in call_outcomes.items():
        if "rerun" in outcomes and outcomes[-1] == "passed":
            flaky.append(nodeid)
    return sorted(flaky)


def load_ledger(ledger_path: Path) -> dict:
    if not ledger_path.exists():
        return {}
    with ledger_path.open() as f:
        data: dict = json.load(f)
        return data


def update_ledger(ledger: dict, flaky_nodeids: list[str], threshold: int) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    for nodeid in flaky_nodeids:
        entry = ledger.get(nodeid, {"count": 0, "first_seen": now})
        entry["count"] = entry.get("count", 0) + 1
        entry.setdefault("first_seen", now)
        entry["last_seen"] = now
        entry["quarantined"] = entry["count"] >= threshold
        ledger[nodeid] = entry
    return dict(sorted(ledger.items()))


def write_quarantine(ledger: dict, quarantine_path: Path) -> None:
    quarantined = sorted(
        nodeid for nodeid, entry in ledger.items() if entry.get("quarantined")
    )
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    with quarantine_path.open("w") as f:
        for nodeid in quarantined:
            f.write(f"{nodeid}\n")


def render_summary(flaky_nodeids: list[str], ledger: dict) -> str:
    if not flaky_nodeids:
        return "No flaky tests detected this run.\n"

    lines = [
        "| Test | Cumulative count | Quarantined |",
        "| --- | --- | --- |",
    ]
    for nodeid in flaky_nodeids:
        entry = ledger.get(nodeid, {})
        count = entry.get("count", "1 (this run)")
        quarantined = "yes" if entry.get("quarantined") else "no"
        lines.append(f"| `{nodeid}` | {count} | {quarantined} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-log", type=Path, required=True)
    parser.add_argument("--mode", choices=["report", "write"], required=True)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--quarantine", type=Path, default=DEFAULT_QUARANTINE)
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    flaky_nodeids = find_flaky_nodeids(args.report_log)
    ledger = load_ledger(args.ledger)

    if args.mode == "write":
        ledger = update_ledger(ledger, flaky_nodeids, args.threshold)
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        with args.ledger.open("w") as f:
            json.dump(ledger, f, indent=2, sort_keys=True)
            f.write("\n")
        write_quarantine(ledger, args.quarantine)

    summary = render_summary(flaky_nodeids, ledger)
    sys.stdout.write(summary)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write("\n## Flaky test report\n\n")
            f.write(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
