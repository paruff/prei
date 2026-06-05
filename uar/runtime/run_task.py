#!/usr/bin/env python3
"""
Minimal PREI task runner — Phase 1 UAR
"""
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

LOG = Path("uar/memory/task_log.jsonl")

def log_event(event: dict):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"ts": datetime.utcnow().isoformat(), **event}) + "\n")

def run_verification() -> bool:
    result = subprocess.run(["make", "check"], capture_output=True, text=True)
    log_event({"type": "verification", "rc": result.returncode, "stdout": result.stdout[-500:]})
    return result.returncode == 0

def execute_task(task_description: str):
    log_event({"type": "task_start", "task": task_description})
    print(f"\n[UAR] Task: {task_description}")
    print("[UAR] Planner: define approach before coding")
    print("[UAR] Coder: implement minimal diff")
    print("[UAR] Running verification...")
    passed = run_verification()
    if passed:
        log_event({"type": "task_pass", "task": task_description})
        print("[UAR] ✅ Verification passed — ready for human review")
    else:
        log_event({"type": "task_fail", "task": task_description})
        print("[UAR] ❌ Verification failed — review uar/memory/task_log.jsonl")
    return passed

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "unspecified task"
    sys.exit(0 if execute_task(task) else 1)
