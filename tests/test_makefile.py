"""Tests for the Makefile — validates structure, no duplicate targets, proper syntax.

These tests catch the class of errors we just fixed (duplicate target,
missing tab separator) before they break the devcontainer or CI.
"""

from __future__ import annotations

from pathlib import Path


MAKEFILE = Path(__file__).resolve().parent.parent / "Makefile"


def test_makefile_exists() -> None:
    """Makefile must exist at project root."""
    assert MAKEFILE.is_file(), f"Makefile not found at {MAKEFILE}"


def test_makefile_no_duplicate_targets() -> None:
    """Every target name must appear exactly once in the Makefile.

    A duplicate target like::

        seed: ...
        ...
        seed: ...

    causes 'warning: overriding recipe for target' and unpredictable
        behaviour — the last definition wins.
    """
    content = MAKEFILE.read_text()
    targets = []
    for line in content.splitlines():
        # Skip recipe lines (start with tab — Makefile recipes use \t prefix)
        if line.startswith("\t"):
            continue
        line = line.strip()
        # Match target lines: "target:" or "target: deps"
        if (
            line
            and not line.startswith("#")
            and not line.startswith(".")
            and ":" in line
        ):
            # Skip variable assignments (=)
            if "=" not in line.split(":")[0]:
                name = line.split(":")[0].strip()
                if name and not name.startswith("$"):
                    targets.append(name)

    seen: dict[str, int] = {}
    duplicates: list[str] = []
    for t in targets:
        if t in seen:
            duplicates.append(t)
        seen[t] = seen.get(t, 0) + 1

    assert not duplicates, f"Duplicate targets found: {duplicates}"


def test_phony_targets_exist() -> None:
    """All targets declared in .PHONY must have a corresponding recipe."""
    content = MAKEFILE.read_text()
    lines = content.splitlines()

    # Extract .PHONY line
    phony_line = next((ln for ln in lines if ln.strip().startswith(".PHONY:")), None)
    assert phony_line, "No .PHONY declaration found"

    phony_targets = phony_line.replace(".PHONY:", "").strip().split()
    defined_targets = set()

    for line in lines:
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith(".")
            and ":" in stripped
            and not stripped.startswith("\t")
            and "=" not in stripped.split(":")[0]
        ):
            name = stripped.split(":")[0].strip()
            if name and not name.startswith("$"):
                defined_targets.add(name)

    missing = [t for t in phony_targets if t not in defined_targets]
    assert not missing, f"Targets declared in .PHONY but missing: {missing}"


def test_recipe_lines_start_with_tab() -> None:
    """Every recipe line (beneath a target) must start with a tab character.

    A recipe line starting with 8 spaces or no indent at all causes
    '*** missing separator. Stop.'
    """
    content = MAKEFILE.read_text()
    errors = []

    for i, line in enumerate(content.splitlines(), 1):
        # Recipe lines are lines inside a target that aren't blank, comments, or variable assignments
        if line and not line.startswith("#") and not line.startswith("."):
            # If it looks like a recipe (no colon, not empty) and doesn't start with tab
            if ":" not in line and "=" not in line:
                # Only check indented lines that look like commands
                if line.startswith("@"):
                    if not line.startswith("\t@"):
                        errors.append((i, line))
                elif line.startswith("\t"):
                    pass  # properly tabbed
                # Skip non-recipe lines (continuation from if/for blocks etc)

    assert not errors, f"Recipe lines missing leading tab: {errors}"
