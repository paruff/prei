# plan-for-today.md (today) — prei

**Horizon**: Today | **Owner**: Dev lead (Phil) | **Review**: End of session

---

## Single Primary Goal

Execute Rentcast spike + FBI CDE retry + docker-compose Postgres — the three P0 parallel spikes.

---

## Target Issues

| Issue | Title | Priority | Status |
|---|---|---|---|
| NEW | Rentcast API spike | P0 | Not started |
| NEW | FBI CDE retry (correct endpoint) | P0 | Not started |
| NEW | docker-compose Postgres + Redis | P0 | Not started |

### Tasks for today

1. **Rentcast spike** — sign up, test API key, verify coverage for TX/FL/TN ZIPs, measure latency
2. **FBI CDE retry** — test correct endpoint with DEMO_KEY: `api.usa.gov/crime/fbi/cde/summary/agencies?state_abbr=TX&year=2023`
3. **docker-compose.yml** — add `db` (Postgres 16) + `redis` services; verify `docker-compose up` healthy
4. **Update settings.py** — `DATABASE_URL` from env, `CELERY_BROKER_URL` from env

---

## TDD Execution Protocol

For each spike:

1. **Red** — Write a one-off script that fails without the thing working
2. **Green** — Run the script; iterate until it passes
3. **Document** — Record findings in spike report (success/fail, latency, coverage, blockers)

### Spike 1: Rentcast

```bash
# test_rentcast.py
import os, requests
key = os.environ["RENTO_METER_API_KEY"]
r = requests.get("https://api.rentcast.io/v1/avm/rent/long-term",
    params={"address": "123 Main St, Austin, TX 78701"},
    headers={"X-Api-Key": key})
print(r.status_code, r.json())
```

**Pass criteria**: 200 OK, `rent` field present, latency < 500ms, coverage for 5 test ZIPs in TX/FL/TN.

### Spike 2: FBI CDE

```bash
# test_fbi_cde.py
import requests
r = requests.get("https://api.usa.gov/crime/fbi/cde/summary/agencies",
    params={"state_abbr": "TX", "year": "2023"}, headers={"X-Api-Key": "DEMO_KEY"})
print(r.status_code, r.json()[:2])
```

**Pass criteria**: 200 OK, returns agency data with offense counts. If 404/403 → document and move to SpotCrime.

### Spike 3: docker-compose

```yaml
# docker-compose.yml (add to existing)
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: prei
      POSTGRES_USER: prei
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes: [postgres_data:/var/lib/postgresql/data]
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

**Pass criteria**: `docker-compose up -d && docker-compose exec db pg_isready` → healthy; app connects with `DATABASE_URL=postgresql://prei:...@localhost:5432/prei`.

---

## Retrospective

*To be filled at end of session*

### What went well
-

### What could improve
-

### Backlog deltas
- New items discovered:
- Items to move to P2:
- Items to reject (scope drift):

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `EXECUTION_QUEUE.md` | What are the weekly priorities? | ↗ links up |
| `MILESTONES.md` | What milestones are we targeting? | ↗ links up |
| `specification.md` | What are the detailed requirements? | parallel |
| `design.md` | How are components designed? | parallel |
