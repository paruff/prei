# CI Fix Report

## Changed

### Files modified

| File | Change |
|---|---|
| `.devcontainer/devcontainer.json:28` | `DATABASE_URL` from `sqlite:////app/db.sqlite3` → `sqlite:////home/vscode/db.sqlite3` |
| `docs/how-to-guides/devcontainer.md:47` | Updated env vars doc from `/app/db.sqlite3` → `/home/vscode/db.sqlite3` |
| `docs/how-to-guides/devcontainer.md:58` | Updated database doc from `/app/db.sqlite3` → `/home/vscode/db.sqlite3` |
| `docs/how-to-guides/devcontainer.md:60` | Updated reset command from `/app/db.sqlite3` → `/home/vscode/db.sqlite3` |
| `docs/how-to-guides/devcontainer.md:97-99` | Updated troubleshooting: fixed path and explanation (devcontainer doesn't use `/app/` or `app` user) |
| `docs/how-to-guides/devcontainer.md:124` | Updated architecture note to explain devcontainer uses vscode user, not app user |
| `README.md:41` | Updated deployment table from `/app/db.sqlite3` → `/home/vscode/db.sqlite3` |

## Root Cause

The devcontainer uses `.devcontainer/Dockerfile` (based on `mcr.microsoft.com/devcontainers/python:1-3.12-bookworm`), which does NOT create `/app/` or an `app` user. When `containerEnv` in `devcontainer.json` set `DATABASE_URL=sqlite:////app/db.sqlite3`, Django tried to write to a directory that neither exists nor is writable by the `vscode` user running the container. This caused `sqlite3.OperationalError: unable to open database file` during `make dev` (which runs `manage.py migrate`).

A prior fix (July 4) moved the root docker-compose.yml's DATABASE_URL to `/app/.runtime/db.sqlite3` (which works because the root Dockerfile creates `/app/` and chowns it to `app` user). The devcontainer was incorrectly using the same `/app/` path without its own Dockerfile creating that directory or user.

## Classification

**Infrastructure Failure** — incorrect filesystem path configuration in the devcontainer environment. No application code was changed.

## Validation

The fix changes the DATABASE_URL to `/home/vscode/db.sqlite3` — the `vscode` user's home directory, which is always writable in the Microsoft devcontainers Python image. This affects:
- `postCreateCommand`: `pip install ... && python manage.py migrate --noinput` — will write to writable path
- `postStartCommand`: `python manage.py check` — will connect to writable database
- `make dev`: `python manage.py migrate && python manage.py runserver` — will use correct path from environment

### Validation steps (to run in Codespace / Dev Container):
1. `python manage.py migrate` — should succeed (creates db at `/home/vscode/db.sqlite3`)
2. `python manage.py check` — should pass
3. `make dev` — should start dev server on port 8000

## Remaining Risks

- The `pycairo` build failure (first log shown by user) is already addressed by `.devcontainer/Dockerfile` line 21, which installs `libcairo2-dev build-essential pkg-config`. This was likely a stale error from before that fix was in place.
- The devcontainer's `Description` section at line 44 says "Built from root `Dockerfile`" which is misleading — it actually uses `.devcontainer/Dockerfile`. This is a pre-existing documentation inaccuracy not introduced by this change.
- The `postCreateCommand` installs all Python dependencies fresh on each Codespace creation. With the correct deps installed in the Dockerfile, this should be fast and reliable.

## Root Cause Category

Infrastructure
