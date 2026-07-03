#!/usr/bin/env python3
"""
Agent accuracy report generator for prei.

Reads .agents/memory/agent_scores.jsonl and produces a monthly report.

Usage:
    python scripts/agent_report.py                  # Current month
    python scripts/agent_report.py --month 2026-06  # Specific month
    python scripts/agent_report.py --all            # All time
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCORES_FILE = Path(".agents/memory/agent_scores.jsonl")

AGENTS = ["planner", "coder", "reviewer", "security", "test-writer"]

DIMENSIONS = {
    "planner": ["completeness", "risk_accuracy", "scope_estimation"],
    "coder": ["first_pass_success", "test_quality", "diff_minimalism"],
    "reviewer": ["false_positives", "false_negatives", "actionable_feedback"],
    "security": ["findings_accuracy", "false_alarm_rate"],
    "test-writer": ["edge_case_coverage", "test_soundness"],
}


def load_scores(month_filter: str | None = None) -> list[dict]:
    """Load scores from JSONL, optionally filtering by month (YYYY-MM)."""
    if not SCORES_FILE.exists():
        return []

    scores = []
    for line in SCORES_FILE.read_text().strip().split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        entry = json.loads(line)
        if month_filter:
            ts = entry.get("ts", "")
            if not ts.startswith(month_filter):
                continue
        scores.append(entry)
    return scores


def compute_averages(scores: list[dict]) -> dict:
    """Compute average scores per agent per dimension."""
    totals: defaultdict[str, defaultdict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    counts: defaultdict[str, int] = defaultdict(int)

    for entry in scores:
        for agent, dims in entry.get("agents", {}).items():
            counts[agent] += 1
            for dim, value in dims.items():
                if isinstance(value, (int, float)):
                    totals[agent][dim].append(value)

    averages: dict[str, dict[str, float | int]] = {}
    for agent in AGENTS:
        if agent not in totals:
            continue
        averages[agent] = {}
        for dim in totals[agent]:
            values = totals[agent][dim]
            if values:
                averages[agent][dim] = round(sum(values) / len(values), 2)
        averages[agent]["_count"] = counts[agent]

    return averages


def collect_corrections(scores: list[dict]) -> list[str]:
    """Collect all human corrections across scores."""
    corrections = []
    for entry in scores:
        corrections.extend(entry.get("human_corrections", []))
    return corrections


def correction_patterns(corrections: list[str]) -> dict[str, int]:
    """Identify common correction patterns."""
    patterns: defaultdict[str, int] = defaultdict(int)

    keywords = {
        "migration": "missed migration",
        "Decimal": "Decimal precision",
        "float": "float usage",
        "test": "test coverage",
        "security": "security issue",
        "scope": "scope estimation",
        "architecture": "architecture violation",
        "boundary": "boundary violation",
        "secret": "secret exposure",
        "auth": "auth issue",
    }

    for correction in corrections:
        lower = correction.lower()
        matched = False
        for keyword, pattern in keywords.items():
            if keyword in lower:
                patterns[pattern] += 1
                matched = True
        if not matched:
            patterns["other"] += 1

    return dict(sorted(patterns.items(), key=lambda x: -x[1]))


def print_report(scores: list[dict], month: str | None):
    """Print the monthly report."""
    label = month or "all time"
    print(f"# Agent Accuracy Report — {label}")
    print(f"# Generated: {datetime.now().isoformat()}")
    print(f"# Total features scored: {len(scores)}")
    print()

    if not scores:
        print("No scores found for this period.")
        return

    averages = compute_averages(scores)

    # Per-agent breakdown
    for agent in AGENTS:
        if agent not in averages:
            continue
        data = averages[agent]
        count = data.pop("_count", 0)
        print(f"## {agent} ({count} scores)")
        print()

        for dim, avg in data.items():
            bar = "█" * int(avg) + "░" * (5 - int(avg))
            status = "🟢" if avg >= 4 else "🟡" if avg >= 3 else "🔴"
            print(f"  {status} {dim:<25} {bar} {avg:.1f}/5")
        print()

    # Correction patterns
    corrections = collect_corrections(scores)
    if corrections:
        patterns = correction_patterns(corrections)
        print("## Top Correction Patterns")
        print()
        for pattern, count in list(patterns.items())[:5]:
            print(f"  {count:>3}x  {pattern}")
        print()

    # Recommendations
    print("## Recommendations")
    print()
    for agent in AGENTS:
        if agent not in averages:
            continue
        data = averages[agent]
        low_dims = [d for d, v in data.items() if isinstance(v, (int, float)) and v < 3]
        if low_dims:
            print(
                f"  - {agent}: scores low on {', '.join(low_dims)} — review role prompt"
            )
    if not any(
        d < 3
        for a in averages.values()
        for d, v in a.items()
        if isinstance(v, (int, float))
    ):
        print("  - All agents performing well — no action needed")
    print()


def main():
    month = None
    show_all = False

    if "--month" in sys.argv:
        idx = sys.argv.index("--month")
        if idx + 1 < len(sys.argv):
            month = sys.argv[idx + 1]
    elif "--all" in sys.argv:
        show_all = True

    scores = load_scores(month if not show_all else None)
    print_report(scores, month if not show_all else "all time")


if __name__ == "__main__":
    main()
