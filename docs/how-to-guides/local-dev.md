# Local Development with Docker (dev environment)

This guide covers running prei locally using Docker Compose with **SQLite** (no external database required).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker Desktop | WSL2 backend (default on Win 11/macOS) |
| Git | `git --version` to verify |

**Windows:** See [Windows Setup](#windows-setup) below for one-time WSL2/Docker config.

---

## Windows Setup (one-time)

### 1. Enable WSL2 and install Ubuntu

```powershell
wsl --install
```

Restart when prompted. After restart, Ubuntu will finish setup and ask for a Linux username/password.

Verify:
```powershell
wsl --status
# Should show "Default Version: 2"
```

### 2. Install Docker Desktop

Download from **[docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)**.

During install:
- Leave **"Use WSL 2 instead of Hyper-V"** checked
- Restart when prompted

### 3. Install Git

**[git-scm.com/download/win](https://git-scm.com/download/win)** — all defaults.

### 4. Configure WSL2 memory

Docker containers get killed if WSL2 memory is too low. Create `C:\Users\<you>\.wslconfig`:

```powershell
notepad $env:USERPROFILE\.wslconfig
```

Add:
```ini
[wsl2]
memory=4GB
processors=2
```

Save, then restart:
```powershell
wsl --shutdown
```
Restart Docker Desktop (right-click tray → Restart).

---

## Step 1 — Clone the repository

```bash
cd ~/dev          # or any folder you prefer
git clone https://github.com/paruff/prei.git
cd prei
```

---

## Step 2 — Create and configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and set **at minimum**:

```env
# Django core
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(50))">
DJANGO_ENV=development
DEBUG=True

# Database (SQLite - default for local dev)
# No Postgres config needed

# Allowed hosts (include 0.0.0.0 for Docker)
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Disable HTTPS enforcement for local HTTP
SECURE_SSL_REDIRECT=False
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
```

> **Why these SSL settings?** The Docker image defaults to production security. Without disabling these, Django redirects every request to `https://`, which causes browser HSTS caching issues locally.

---

## Step 3 — Start the stack

```bash
docker compose up -d
```

This starts one container:
- `prei-web-1` — Django/Gunicorn app with SQLite database

Verify:
```bash
docker compose ps
# Should show "Up" and "healthy"

docker compose logs web --tail 20
# Look for "Listening at: http://0.0.0.0:8000"
```

---

## Step 4 — Open the app

```
http://127.0.0.1:8000/
```

Demo login:
| Field | Value |
|---|---|
| Email | `demo@prei.dev` |
| Password | `DemoPass123!` |

Admin: `http://127.0.0.1:8000/admin/`

---

## Troubleshooting

### Browser timeout / connection refused

1. `docker compose ps` — confirm container is Up/healthy
2. `docker exec prei-web-1 wget -O- http://localhost:8000/api/health/` — should return `{"status":"ok"}`
3. `docker compose logs web --tail 30` — check for errors

### Browser redirects to `https://` and hangs

Clear HSTS cache:

**Brave:** `brave://net-internals/#hsts`
**Chrome:** `chrome://net-internals/#hsts`

Delete `localhost` and `127.0.0.1` from "Delete domain security policies". Fully quit and reopen browser.

### Container gets SIGKILL / OOM

Increase WSL2 memory (see [Windows Setup](#windows-setup) step 4). Verify:
```bash
docker stats --no-stream
```

---

## Stopping

```bash
docker compose down
```

Data persists in the container's `/app/db.sqlite3`. To wipe everything:
```bash
docker compose down -v
```

---

## Useful Commands

| Command | Purpose |
|---|---|
| `docker compose up -d` | Start in background |
| `docker compose down` | Stop |
| `docker compose logs web --tail 30` | Recent logs |
| `docker compose ps` | Container status |
| `docker stats --no-stream` | Memory/CPU snapshot |
| `docker exec -it prei-web-1 bash` | Shell in container |
