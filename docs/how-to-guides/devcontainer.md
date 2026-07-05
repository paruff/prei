# Dev Container / GitHub Codespaces (test)

This guide covers running prei in a **VS Code Dev Container** or **GitHub Codespace** — the `test` environment.

---

## Prerequisites

| Platform | Requirement |
|---|---|
| **GitHub Codespaces** | GitHub account, repo access |
| **VS Code Dev Containers** | VS Code + "Dev Containers" extension + Docker Desktop |

---

## Quick Start

### GitHub Codespaces (browser-based)

1. Open the repo on GitHub
2. Click **Code → Codespaces → Create codespace on main**
3. Wait for build (~2 minutes)
4. In the integrated terminal:
   ```bash
   make dev
   ```
5. Open the forwarded port **8000** (toast notification → "Open in Browser")
6. Visit `http://localhost:8000`

### VS Code Dev Container (local)

1. Open repo in VS Code: `code .`
2. Command Palette (`Ctrl+Shift+P`) → **Dev Containers: Reopen in Container**
3. Wait for build
4. Terminal → `make dev`
5. Open forwarded port 8000

---

## What Happens Automatically

The `.devcontainer/devcontainer.json` configures:

- **Base image:** Built from root `Dockerfile` (Python 3.12, non-root `app` user)
- **Compose file:** Uses root `docker-compose.yml` (SQLite, no Postgres)
  - **Environment variables:**
    - `DATABASE_URL=sqlite:////home/vscode/db.sqlite3` (absolute path — writable by `vscode` user)
  - `DEBUG=True`, `ALLOWED_HOSTS=*`, `SECRET_KEY=dev-secret-key-change-me`
  - `RUN_MIGRATIONS=1`
- **Post-create:** `pip install -r requirements.txt && python manage.py migrate --noinput`
- **Post-start:** `python manage.py check`
- **Port forward:** 8000 → labeled "Django app"

---

## Database

- **SQLite** at `/home/vscode/db.sqlite3` (inside container, not the bind-mounted workspace)
- Persists across container restarts but **not** across Codespace rebuilds
- To reset: delete `/home/vscode/db.sqlite3` and re-run `make dev`

---

## Useful Commands

| Command | Purpose |
|---|---|
| `make dev` | Run migrations + start Django runserver on 0.0.0.0:8000 |
| `make superuser` | Create admin user (first time only) |
| `make lint` | Ruff + format check |
| `make test` | Run pytest suite |
| `make check` | `manage.py check` + lint + tests |

---

## Demo Login

| Field | Value |
|---|---|
| Email | `demo@prei.dev` |
| Password | `DemoPass123!` |

Created by `make dev` via `seed_data` management command.

---

## Troubleshooting

### Port 8000 not forwarded
- VS Code: Ports tab → check 8000 is listed → right-click → "Preview in Browser"
- Codespaces: Ports panel → visibility → "Public" or "Private"

### "DisallowedHost" error
- Ensure `ALLOWED_HOSTS=*` is set (it is in devcontainer.json)
- If using custom domain, add to `ALLOWED_HOSTS` in `.env`

### Database "unable to open database file"
- Fixed in devcontainer.json: `DATABASE_URL=sqlite:////home/vscode/db.sqlite3` (absolute path)
- The Dev Container uses `mcr.microsoft.com/devcontainers/python` (not the root Dockerfile) and runs as `vscode`, so `/home/vscode/` is the writable home directory

### Changes not reflecting
- Dev container mounts workspace at `/workspaces/prei` but Django runs from `/app`
- Code is **copied** into `/app` at build time (see Dockerfile `COPY . .`)
- For live reload, use `make dev` which runs Django's runserver with auto-reload watching `/app`

---

## Architecture Note

```
┌─────────────────────────────────────────────────────┐
│  GitHub Codespace / VS Code Dev Container           │
│  ┌─────────────────────────────────────────────┐   │
│  │  Workspace mount: /workspaces/prei (source)  │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │  Container FS: /app (Django runs here)       │   │
│  │    ├── db.sqlite3  ← writable (chowned)      │   │
│  │    └── ...                                    │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

The source is mounted at `/workspaces/prei` for git/editor access, but the **runtime** code lives at `/app` (copied during `docker build`). The Dev Container uses its own Dockerfile (`.devcontainer/Dockerfile`) based on `mcr.microsoft.com/devcontainers/python:1-3.12-bookworm`. The database goes to `/home/vscode/db.sqlite3` — the `vscode` user's home directory — because the devcontainer runs as `vscode`, not `app`.
