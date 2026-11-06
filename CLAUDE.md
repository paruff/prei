@AGENTS.md

## Shell
Run shell commands with `bash` (`/usr/local/bin/bash`, 5.x), not zsh: zsh does not word-split
unquoted variables (e.g. `$files`) and errors on unmatched globs. Use `bash -c '...'` for anything
that relies on either.

## Tests (host venv)
- Run `.venv/bin/python -m pytest <paths>`. `pytest.ini` addopts already set `--reruns 1`, `--report-log` and `-m "unit or integration"`.
  Don't pass `-p no:rerunfailures` (breaks `--reruns`) or `-n` (no xdist). Use `--reruns 0` to turn retries off.
- The full suite takes ~10 min: run it in the background, or pass paths.
- PDF export tests drive the venv's Playwright (1.62), which needs its own `chromium_headless_shell-1234` in
  `~/Library/Caches/ms-playwright`, not the system Chrome or the MCP Playwright browser. If they fail with
  "Executable doesn't exist", run `.venv/bin/python -m playwright install chromium-headless-shell` (prebuilt download, allowed).

## EGM
EGM artifact directory: .dev/egm
