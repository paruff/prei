"""
Context processor to provide version and environment info to all templates.

Sources (in priority order for version/commit):
1. ``/app/.meta/{version,commit}`` — baked-in during Docker build
2. ``PREI_VERSION`` / ``PREI_COMMIT`` env vars — injected during Docker build
3. Git tag matching current HEAD (loose refs then packed-refs) — dev
4. ``0.0.0-dev`` / ``unknown`` — fallback

Exposed template variables:
- ``version`` — e.g. "0.2.2"
- ``git_commit`` — short SHA, e.g. "a1b2c3d" or "a1b2c3d-dirty"
- ``api_keys_configured`` — bool, True when both CENSUS_API_KEY and BLS_API_KEY are set
- ``census_key_configured`` — bool
- ``bls_key_configured`` — bool
"""

from __future__ import annotations

import logging
from os import getenv
from pathlib import Path

logger = logging.getLogger("prei.config")

# Number of characters for short commit SHA
_SHORT_SHA_LENGTH = 7


def _read_version() -> str:
    """Read version from baked-in file (Docker) or git tag (dev).

    Priority:
    1. ``/app/.meta/version`` — written during Docker build
    2. ``PREI_VERSION`` env var — injected during Docker build
    3. Git tag matching HEAD — local development
    4. ``0.0.0-dev`` — fallback
    """
    # 1. Baked-in file (Docker builds)
    try:
        text = Path("/app/.meta/version").read_text().strip()
        if text:
            return text
    except FileNotFoundError, OSError:
        pass

    # 2. Environment variable (injected by Docker build)
    env_version = getenv("PREI_VERSION")
    if env_version:
        return env_version

    # 3. Git tag matching HEAD (development)
    git_dir = _find_git_dir()
    if git_dir is not None:
        tag = _read_current_tag(git_dir)
        if tag:
            return tag

    return "0.0.0-dev"


def _read_build_date() -> str:
    """Read build date from baked-in file (Docker) or return empty string.

    Priority:
    1. ``/app/.meta/build-date`` — written during Docker build
    2. ``BUILD_DATE`` env var
    3. ``""`` — fallback (local dev)
    """
    try:
        text = Path("/app/.meta/build-date").read_text().strip()
        if text:
            return text
    except FileNotFoundError, OSError:
        pass

    env_date = getenv("BUILD_DATE")
    if env_date:
        return env_date

    return ""


def _read_git_commit() -> str:
    """Read short commit SHA from baked-in file (Docker) or git (dev).

    Priority:
    1. ``/app/.meta/commit`` — written during Docker build
    2. ``PREI_COMMIT`` env var — injected during Docker build
    3. Git HEAD ref parsing via filesystem (no subprocess) — for dev snapshot
    4. ``unknown`` — fallback
    """
    # 1. Baked-in file (Docker builds)
    try:
        text = Path("/app/.meta/commit").read_text().strip()
        if text:
            return text[:_SHORT_SHA_LENGTH]
    except FileNotFoundError, OSError:
        pass

    # 2. Environment variable (injected by Docker build)
    env_commit = getenv("PREI_COMMIT")
    if env_commit:
        return env_commit[:_SHORT_SHA_LENGTH]

    # 3. Git HEAD (development)
    git_dir = _find_git_dir()
    if git_dir is None:
        return "unknown"

    sha = _resolve_head(git_dir)
    if not sha:
        return "unknown"

    short_sha = sha[:_SHORT_SHA_LENGTH]

    # Best-effort dirty check: if HEAD resolves to a packed ref that differs
    # from the reftable or if there's an index diff.  This is a filesystem-
    # only approximation; the CI build always gets a clean checkout so the
    # dirty flag only matters in local dev.
    if _is_dirty(git_dir):
        return f"{short_sha}-dirty"

    return short_sha


def _find_git_dir() -> Path | None:
    """Find the ``.git`` directory walking up from the project root."""
    candidate = Path(__file__).resolve().parent.parent / ".git"
    if candidate.is_dir():
        return candidate
    # Handle worktrees where .git is a file pointing to the real gitdir
    if candidate.is_file():
        try:
            text = candidate.read_text().strip()
            if text.startswith("gitdir: "):
                gitdir_path = Path(text[8:].strip())
                if gitdir_path.is_dir():
                    return gitdir_path
        except FileNotFoundError, OSError:
            pass
    return None


def _resolve_head(git_dir: Path) -> str | None:
    """Resolve HEAD to a full commit SHA."""
    head_file = git_dir / "HEAD"
    try:
        head_content = head_file.read_text().strip()
    except FileNotFoundError, OSError:
        return None

    if not head_content:
        return None

    # Symbolic ref: "ref: refs/heads/main"
    if head_content.startswith("ref: "):
        ref_path = head_content[5:].strip()
        ref_file = git_dir / ref_path
        try:
            return ref_file.read_text().strip()
        except FileNotFoundError, OSError:
            # Packed ref — attempt to look up in packed-refs
            return _resolve_packed_ref(git_dir, ref_path)

    # Detached HEAD — the SHA is directly in the file
    return head_content


def _resolve_packed_ref(git_dir: Path, ref_path: str) -> str | None:
    """Look up a reference in ``.git/packed-refs``."""
    packed = git_dir / "packed-refs"
    if not packed.is_file():
        return None
    try:
        for line in packed.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1] == ref_path:
                return parts[0]
    except FileNotFoundError, OSError:
        pass
    return None


def _read_current_tag(git_dir: Path) -> str | None:
    """Read the current tag from HEAD's position.

    Searches loose refs in ``.git/refs/tags/`` first, then falls back to
    ``packed-refs``.  Returns the first matching tag for the current HEAD
    commit, or ``None``.
    """
    sha = _resolve_head(git_dir)
    if not sha:
        return None

    # 1. Loose refs: each file under refs/tags/ is one tag
    tags_dir = git_dir / "refs" / "tags"
    if tags_dir.is_dir():
        try:
            for tag_file in sorted(tags_dir.iterdir()):
                if tag_file.is_file():
                    try:
                        if tag_file.read_text().strip() == sha:
                            return tag_file.name
                    except FileNotFoundError, OSError:
                        continue
        except OSError:
            pass

    # 2. Packed refs
    packed = git_dir / "packed-refs"
    if packed.is_file():
        try:
            for line in packed.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("^"):
                    continue
                parts = line.split(" ", 1)
                if (
                    len(parts) == 2
                    and parts[0] == sha
                    and parts[1].startswith("refs/tags/")
                ):
                    return parts[1].removeprefix("refs/tags/")
        except FileNotFoundError, OSError:
            pass

    return None


def _is_dirty(git_dir: Path) -> bool:
    """Approximate dirty check by comparing HEAD ref timestamps.

    This is a best-effort, filesystem-only heuristic.  It returns ``True``
    if any tracked file under the repo root is newer than the HEAD ref's
    modification time.  This avoids ``subprocess`` entirely.
    """
    head_ref = _head_ref_file(git_dir)
    if head_ref is None:
        return False

    try:
        ref_mtime = head_ref.stat().st_mtime
    except OSError:
        return False

    project_root = git_dir.parent
    # Check a few key directories for newer mtime
    for subdir in ("core", "templates", "static", "tests"):
        path = project_root / subdir
        if not path.is_dir():
            continue
        try:
            for entry in path.rglob("*.py"):
                if entry.stat().st_mtime > ref_mtime + 1:
                    return True
        except OSError:
            continue
    return False


def _head_ref_file(git_dir: Path) -> Path | None:
    """Return the Path to the file HEAD points to, or None."""
    head_file = git_dir / "HEAD"
    try:
        content = head_file.read_text().strip()
    except FileNotFoundError, OSError:
        return None

    if content.startswith("ref: "):
        ref_path = content[5:].strip()
        ref_file = git_dir / ref_path
        if ref_file.is_file():
            return ref_file
        # Packed refs — use HEAD itself as timestamp proxy
        return head_file

    # Detached HEAD
    return head_file


def version(request):  # type: ignore[no-untyped-def]
    """Add version, git_commit, and api key status to every template context."""
    census_key = getenv("CENSUS_API_KEY", "")
    bls_key = getenv("BLS_API_KEY", "")

    return {
        "version": _read_version(),
        "git_commit": _read_git_commit(),
        "build_date": _read_build_date(),
        "api_keys_configured": bool(census_key and bls_key),
        "census_key_configured": bool(census_key),
        "bls_key_configured": bool(bls_key),
    }
