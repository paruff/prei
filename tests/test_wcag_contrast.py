"""FR-16 / G5.3: the primary fill reads with white text and focus stays visible."""

import re
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "static" / "css"


def _lum(hex_):
    c = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def test_primary_fill_has_aa_contrast_with_white():
    tokens = (CSS / "tokens.css").read_text()
    match = re.search(r"--color-grow-700:\s*(#\w{6})", tokens)
    assert match
    grow = match.group(1)
    assert re.search(r"--color-primary:\s*var\(--color-grow-700\)", tokens)
    assert 1.05 / (_lum(grow) + 0.05) >= 4.5


def test_no_text_uses_neutral_200_and_focus_visible_exists():
    base = (CSS / "base.css").read_text() + (CSS / "pipeline.css").read_text()
    assert not re.search(r"(?<![-\w])color:\s*var\(--color-neutral-200\)", base)
    assert re.search(r":focus-visible\s*\{[^}]*outline:\s*2px", base)
    assert not re.search(r"outline:\s*(none|0)\b", base)


def test_neutral_500_text_has_aa_contrast_on_every_surface():
    tokens = (CSS / "tokens.css").read_text()
    match = re.search(r"--color-neutral-500:\s*(#\w{6})", tokens)
    assert match
    text = match.group(1)
    for surface in ("#FFFFFF", "#F8F8F6", "#F1EFE8"):
        ratio = (_lum(surface) + 0.05) / (_lum(text) + 0.05)
        assert ratio >= 4.5, (surface, ratio)
