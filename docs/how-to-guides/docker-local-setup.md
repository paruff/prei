# How to Run prei Locally with Docker

This guide covers running the published `ghcr.io/paruff/prei:latest` container image
on a local Windows 11 machine using Docker Desktop and Docker Compose.

---

## Windows Environment Setup

Do this once on a fresh Windows 11 machine. Skip any step you've already completed.

### 1. Enable Hyper-V

Open PowerShell as Administrator and run:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

Restart when prompted.

### 2. Install WSL2 and Linux

```powershell
wsl --install
```

This installs WSL2 and Ubuntu (the default distro). Restart when prompted.
After restart, Ubuntu will finish setting up and ask you to create a Linux username and password.

Verify WSL2 is active:

```powershell
wsl --status
```

Should show `Default Version: 2`.

### 3. Install Docker Desktop

Download directly from **[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)** (preferred) or from the Microsoft Store — either works.

During installation:
- Leave **"Use WSL 2 instead of Hyper-V"** checked (default)
- Restart when prompted

After Docker Desktop starts, verify it's running:

```powershell
docker --version
```

### 4. Install Git

Download from **[https://git-scm.com/download/win](https://git-scm.com/download/win)** — all defaults are fine.

Verify:

```powershell
git --version
```

### 5. Install Python (if not already present)

Required to generate a `SECRET_KEY`. Download from **[https://www.python.org/downloads/](https://www.python.org/downloads/)**.

> ⚠️ During installation check **"Add Python to PATH"** or the `python` command won't work in PowerShell.

Verify:

```powershell
python --version
```

### 6. Configure WSL2 memory

By default WSL2 gets very little memory, which causes Docker containers to get killed.
Create `C:\Users\<you>\.wslconfig`:

```powershell
notepad $env:USERPROFILE\.wslconfig
```

Add:

```ini
[wsl2]
memory=4GB
processors=2
```

Save, then restart WSL:

```powershell
wsl --shutdown
```

Restart Docker Desktop (right-click tray icon → Restart).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker Desktop | WSL2 backend (default on Win 11) |
| Git | `git --version` to verify |
| 4 GB+ RAM allocated to WSL2 | See step below |

### Allocate enough memory to WSL2

Docker Desktop on Windows uses WSL2, which defaults to a low memory ceiling.
Create or edit `C:\Users\<you>\.wslconfig`:

```ini
[wsl2]
memory=4GB
processors=2
```

Then restart WSL and Docker Desktop:

```powershell
wsl --shutdown
# Right-click Docker Desktop tray icon → Restart
```

---

## Step 1 — Clone the repository

```powershell
cd C:\dev          # or any folder you prefer
git clone https://github.com/paruff/prei.git
cd prei
```

---

## Step 2 — Create and configure `.env`

```powershell
copy .env.example .env
notepad .env
```

Set **at minimum** these values:

### Generate a SECRET_KEY

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copy the output and paste it as the value.

### Required `.env` settings for local development

```env
# Django core
SECRET_KEY=<paste generated key here>
DJANGO_ENV=development

# Database
POSTGRES_PASSWORD=<pick any password>

# Allowed hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# Disable HTTPS enforcement (required for local HTTP access)
SECURE_SSL_REDIRECT=False
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
```

> **Why the SSL settings?** The published image defaults to production security settings.
> Without disabling these locally, Django redirects every request to `https://`, which
> causes browser HSTS caching issues that are painful to undo.

---

## Step 3 — Start the stack

```powershell
docker compose up -d
```

This pulls and starts two containers:
- `prei-web-1` — Django/Gunicorn app
- `prei-db-1` — PostgreSQL 16 database

Verify both are healthy:

```powershell
docker compose ps
```

Both should show `Up` and `healthy`. Check logs if needed:

```powershell
docker compose logs web --tail 30
```

Look for `Listening at: http://0.0.0.0:8000` to confirm Gunicorn is serving.

---

## Step 4 — Open the app

```
http://127.0.0.1:8000/
```

Log in with the seeded demo account:

| Field | Value |
|---|---|
| Email | `demo@prei.dev` |
| Password | `DemoPass123!` |

Admin interface:

```
http://127.0.0.1:8000/admin/
```

---

## Troubleshooting

### Browser shows a timeout or refuses to connect

1. Confirm containers are running: `docker compose ps`
2. Confirm the app is healthy inside the container:
   ```powershell
   docker exec prei-web-1 wget -O- http://localhost:8000/api/health/
   # should return {"status":"ok"}
   ```
3. Check logs: `docker compose logs web --tail 30`

### Browser redirects to `https://` and hangs

Your browser has cached an HSTS policy from a previous run. Clear it:

**Brave:**
```
brave://net-internals/#hsts
```

**Chrome:**
```
chrome://net-internals/#hsts
```

In the **Delete domain security policies** field, delete both:
- `localhost`
- `127.0.0.1`

Then fully quit and reopen the browser (don't just open a new tab).

If still not working, clear cached images only (**not cookies**) from the last hour:

**Brave:** `brave://settings/clearBrowserData`
**Chrome:** `chrome://settings/clearBrowserData`

> ⚠️ Do **not** clear All Time + Cookies unless you want to be logged out of every site.
> Cached images for the last hour is sufficient to fix HSTS issues.

### Workers keep getting SIGKILL

Check WSL2 memory allocation — see the Prerequisites section above.
Verify current usage:

```powershell
docker stats --no-stream
```

---

## Stopping the stack

```powershell
docker compose down
```

Data is persisted in a Docker volume (`prei_postgres_data`) so your database
survives restarts. To wipe everything including the database:

```powershell
docker compose down -v
```

---

## Useful commands

| Command | Purpose |
|---|---|
| `docker compose up -d` | Start stack in background |
| `docker compose down` | Stop stack |
| `docker compose logs web --tail 30` | Recent web logs |
| `docker compose ps` | Container status |
| `docker stats --no-stream` | Memory/CPU snapshot |
| `docker exec -it prei-web-1 bash` | Shell inside web container |
