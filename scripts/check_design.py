#!/usr/bin/env python3
"""design-lint: enforce DESIGN.md "Don'ts" on templates and static CSS.

Rules: undefined-var, hex-color, rgb-color, style-block, bootstrap-class.
Today's violations live in scripts/design_allowlist.txt as `path rule token count`
lines; a count above the entry fails (new violation), below it also fails (shrink
the entry). `--write-allowlist` regenerates the file from the current tree.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = Path(__file__).with_name("design_allowlist.txt")
TOKENS = Path("static/css/tokens.css")
EXPORTS = "templates/exports/"  # PDF export keeps inline styles and hex (DESIGN.md)

VAR_USE = re.compile(r"var\(\s*(--[\w-]+)")
VAR_DEF = re.compile(r"(--[\w-]+)\s*:")
HEX = re.compile(
    r"(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])"
)
ANCHOR = re.compile(r"""(?:href|hx-target|hx-swap-oob)=["']$""")
RGB = re.compile(r"\brgba?\(")
STYLE = re.compile(r"<style\b")
CLASS_ATTR = re.compile(r'class="([^"]*)"')
COMMENT = re.compile(r"/\*.*?\*/|<!--.*?-->|\{#.*?#\}", re.S)
BOOTSTRAP = re.compile(
    r"^(col(-(xs|sm|md|lg|xl|xxl))?(-\d+)?|row|container(-fluid)?"
    r"|d-(flex|none|block|inline|inline-block|grid)|justify-content-.+|align-items-.+"
    r"|[mp][trblxy]?-\d|w-\d+|h-\d+|fw-.+|fs-\d|float-.+"
    r"|form-(control|group|select|check|check-.+)|input-group.*|navbar.*"
    r"|badge|bg-.+|text-(muted|primary|danger|success|warning|info|center|right|left|white|dark)"
    r"|btn-(secondary|success|danger|warning|info|light|dark|link|outline-.+|sm|lg)"
    r"|table-(striped|bordered|hover|responsive)|alert(-.+)?"
    r"|card-(header|body|footer|title|text)|list-group.*|modal.*|dropdown.*"
    r"|small|lead|display-\d|spinner-.+|jumbotron|close|collapse|sr-only)$"
)


def scan(root: Path = ROOT) -> Counter:
    css = sorted((root / "static/css").glob("*.css"))
    html = sorted((root / "templates").rglob("*.html"))
    texts = {
        p: COMMENT.sub(lambda m: "\n" * m.group().count("\n"), p.read_text())
        for p in css + html
    }
    defined = {n for t in texts.values() for n in VAR_DEF.findall(t)}
    project_classes = {
        c for p in css for c in re.findall(r"\.([A-Za-z_][\w-]*)", texts[p])
    }
    found: Counter = Counter()
    for path, text in texts.items():
        rel = path.relative_to(root).as_posix()
        is_tokens = rel == TOKENS.as_posix()
        is_export = rel.startswith(EXPORTS)
        for name in VAR_USE.findall(text):
            if name not in defined:
                found[(rel, "undefined-var", name)] += 1
        if not is_tokens and not is_export:
            for m in HEX.finditer(text):
                if not ANCHOR.search(text[max(0, m.start() - 12) : m.start()]):
                    found[(rel, "hex-color", m.group().lower())] += 1
            for _ in RGB.finditer(text):
                found[(rel, "rgb-color", "rgb(")] += 1
        if path.suffix == ".html":
            if not is_export and STYLE.search(text):
                found[(rel, "style-block", "<style>")] += len(STYLE.findall(text))
            for attr in CLASS_ATTR.findall(text):
                for cls in attr.split():
                    if BOOTSTRAP.match(cls) and cls not in project_classes:
                        found[(rel, "bootstrap-class", cls)] += 1
    return found


def read_allowlist() -> Counter:
    allowed: Counter = Counter()
    if ALLOWLIST.exists():
        for line in ALLOWLIST.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                path, rule, token, count = line.rsplit(" ", 3)
                allowed[(path, rule, token)] = int(count)
    return allowed


def main(argv: list[str]) -> int:
    found = scan()
    if "--write-allowlist" in argv:
        lines = [f"{p} {r} {t} {n}" for (p, r, t), n in sorted(found.items())]
        ALLOWLIST.write_text(
            "# design-lint allow-list: path rule token count. Shrink it; never grow it.\n"
            "# Regenerate with: python3 scripts/check_design.py --write-allowlist\n"
            + "\n".join(lines)
            + "\n"
        )
        print(f"wrote {len(lines)} entries")
        return 0
    allowed = read_allowlist()
    errors = []
    for key, n in sorted(found.items()):
        if n > allowed[key]:
            errors.append(
                f"{key[0]}: {key[1]} {key[2]!r} x{n} (allowed {allowed[key]}), see DESIGN.md Do's and Don'ts"
            )
    for key, n in sorted(allowed.items()):
        if found[key] < n:
            errors.append(
                f"{key[0]}: {key[1]} {key[2]!r} fixed ({found[key]} < {n}), lower it in scripts/design_allowlist.txt"
            )
    print("\n".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
