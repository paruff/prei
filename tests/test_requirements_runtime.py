"""requirements-runtime.txt is a hand-copied subset: its pins must match requirements.txt."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _pins(name: str) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in (ROOT / name).read_text().splitlines():
        line = line.split("#")[0].strip()
        if "==" in line:
            package, version = line.split("==", 1)
            pins[package.strip().lower()] = version.strip()
    return pins


@pytest.mark.unit
def test_runtime_pins_match_full_pins() -> None:
    full = _pins("requirements.txt")
    runtime = _pins("requirements-runtime.txt")

    assert runtime, "requirements-runtime.txt has no pins"
    mismatched = {
        package: (version, full.get(package))
        for package, version in runtime.items()
        if full.get(package) != version
    }
    assert not mismatched, f"runtime pin differs from requirements.txt: {mismatched}"
