# Developer Experience — prei

> Notes on local development environment, tooling, and workflow.

---

## Local Dev Environment Setup

### Recommended: VS Code with Dev Containers

This is what teams building production Django apps use. It gives you:

```
┌─────────────────────────────────────────────────────────┐
│ VS Code Window                                          │
│ ┌──────────┬────────────────────────┬────────────────┐  │
│ │ Explorer │                        │  Browser       │  │
│ │ (source) │   Code Editor          │  Preview       │  │
│ │          │   (active file)        │  (app running) │  │
│ │          │                        │                │  │
│ ├──────────┤                        │                │  │
│ │ GitLens  │                        │                │  │
│ │ (history)│                        │                │  │
│ │          │                        │                │  │
│ │          │                        │                │  │
│ └──────────┴────────────────────────┴────────────────┘  │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Terminal: agent chat + make commands                │ │
│ │ $ make test-acceptance                              │ │
│ │ $ python manage.py runserver                        │ │
│ └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### VS Code Extensions

| Extension | Purpose |
|---|---|
| **Dev Containers** (`ms-vscode-remote.remote-containers`) | Reproducible environment for everyone |
| **Python** (`ms-python.python`) | Linting, debugging, test runner |
| **Django** (`batisteo.vscode-django`) | Template syntax, HTML support |
| **GitLens** (`eamodio.gitlens`) | Blame, history, diff |
| **Live Preview** (`ms-vscode.live-preview`) | Browser preview inside VS Code |
| **GitHub Actions** (`github.vscode-github-actions`) | Workflow editing |
| **Even Better TOML** (`tamasfe.even-better-toml`) | pyproject.toml support |
| **Ruff** (`charliermarsh.ruff`) | Format on save |

### Dev Container Setup (recommended)

```json
// .devcontainer/devcontainer.json
{
  "name": "prei",
  "image": "mcr.microsoft.com/devcontainers/python:3.14",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {}
  },
  "postCreateCommand": "pip install -r requirements.txt",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "batisteo.vscode-django",
        "eamodio.gitlens",
        "github.vscode-github-actions",
        "charliermarsh.ruff"
      ]
    }
  },
  "forwardPorts": [8000]
}
```

### Running the App Locally

```bash
# Start the Django dev server (hot reload enabled)
make dev

# Or manually:
python manage.py runserver 8000

# Open browser: http://localhost:8000
```

### Running Tests

```bash
# All unit tests (fast, no Docker needed)
make test

# Acceptance tests (needs Docker container running)
make test-acceptance

# Financial math verification (58 edge cases)
make test-finance-math

# Live BDD tests (needs Docker)
make test-live
```

---

## Current State: What We're Using

| Tool | Status |
|---|---|
| VS Code | ✅ Primary IDE |
| Dev Containers | ⬜ Not yet configured |
| Live Preview | ⬜ Not installed — use external browser |
| Terminal | ✅ Built-in VS Code terminal |
| GitLens | ⬜ Not installed |
| Ruff extension | ⬜ Not installed |

### Quick Start (today, no devcontainer)

```
Terminal panel (bottom):
  $ python manage.py runserver 8000
  # App running at http://localhost:8000

Browser (right side or separate window):
  Open http://localhost:8000

Source (left side):
  VS Code file explorer
```

---

## Expert Recommendation (25-year veteran)

> "The best setup is the one that minimizes context switches. Your brain
> should never leave the problem domain. Every time you alt-tab from
> editor to browser to terminal, you lose 15 seconds of context. Multiply
> by 200 switches per day = 50 minutes of lost flow state."
>
> **Setup priority:**
> 1. Dev container first — ensures everyone has identical environment
> 2. Browser preview INSIDE VS Code — no alt-tab to Chrome
> 3. Terminal as editor panel — not floating, not separate window
> 4. Test runner in editor — green/red dots next to function names
> 5. Format on save — never think about whitespace again
>
> "Don't optimize for the tool. Optimize for staying in the problem domain."
