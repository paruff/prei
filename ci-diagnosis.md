Failure:      devcontainer — `docker compose up` → sqlite3.OperationalError: unable to open database file
Location:     .devcontainer/devcontainer.json (DATABASE_URL), Dockerfile line 49 (chown), investor_app/settings.py line 9 (BASE_DIR)
Evidence:     Container log shows `django.db.utils.OperationalError: unable to open database file` at startup, looping through `web-1 exited with code 1 (restarting)`. Stack trace originates from `django/db/backends/sqlite3/base.py:206` — sqlite3 cannot open or create the database file at the resolved path.
Likely Cause: Devcontainer bind-mounts repo to `/workspaces/prei` (root-owned); `BASE_DIR` resolves to `/workspaces/prei`; relative `DATABASE_URL=sqlite:///db.sqlite3` resolves to `/workspaces/prei/db.sqlite3` which `app` user cannot write to since the bind mount is root-owned. The Dockerfile `chown` only covers `/app`, not the runtime bind mount.
Confidence:   HIGH
Proposed Fix: Use absolute path `sqlite:////app/db.sqlite3` in devcontainer.json containerEnv, since `/app` is chowned to `app:app` in the Dockerfile and is always writable regardless of where the code is mounted.
