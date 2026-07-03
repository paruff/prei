"""
Context processor to provide version information to all templates.
Reads version from VERSION file at project root.
"""

from pathlib import Path


def version(request):
    """
    Context processor to add version to all template contexts.
    Reads from VERSION file at project root.
    """
    version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
    try:
        version_str = version_file.read_text().strip()
    except FileNotFoundError:
        version_str = "0.0.0-dev"
    return {"version": version_str}
