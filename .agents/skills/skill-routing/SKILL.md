# Skill Routing Skill — prei

Routes *external* skills (Claude Code / ECC catalog) for this repo. The nine
sibling packs in `.agents/skills/` remain canonical for prei-specific rules —
this file only decides which of the several hundred general-purpose skills are
worth loading here, and which are noise.

## When to load
- Starting a session and deciding what context to pull in
- An agent proposes a skill that has no bearing on this stack
- Onboarding a new agent, model, or contributor to the repo

## Stack of record

Django 6.0 + DRF 3.18 on Python 3.14 · PostgreSQL in production (SQLite in dev)
· Django templates + PWA, no JS framework · Playwright (E2E **and** PDF export)
· numpy-financial · gunicorn + WhiteNoise · Docker → Render · structlog.

No Celery. No Redis. No TypeScript, React, or Vue. `package.json` is a script
shim only — it is not a frontend build.

## DAILY — load by default

Each entry names the repo evidence that earns it. Remove any entry whose
evidence stops being true.

| Skill | Evidence in this repo |
|---|---|
| `django-patterns` | Django 6.0.7 + DRF; `core/` is the whole application |
| `django-security` | Hardening in `settings.py` is gated on `not DEBUG`, not `IS_PRODUCTION` — fail-open |
| `django-tdd` | 2,300+ tests, but 88% are `integration`; marker discipline is the fix |
| `python-testing` | `pytest.ini` drives markers, reruns, and report-log |
| `python-patterns` | 362 Python files, ~40k non-test lines |
| `docker-patterns` | Multi-stage Dockerfile is the deployable unit; PDF export broke because the image was never tested |
| `deployment-patterns` | `render.yaml`, compose base + production overlay, `post-deployment.yml` |
| `database-migrations` | 52 migrations including a merge migration (`0049_merge`); rollback untested |
| `postgres-patterns` | `psycopg2-binary` in production |
| `contract-first` | Four external adapters; Census returns `population: 0` while `population_current` is populated |
| `api-design` | Large DRF surface; foreclosures endpoint leaks `ErrorDetail(...)` reprs to users |
| `github-ops` | Nine workflows, release-please, Dependabot, 21/24 actions on mutable tags |
| `verification-loop` | `make smoke` exits 0 no matter what it finds |
| `error-handling` | Ten `except Exception: pass` sites outside tests |

Pair with the superpowers process skills, which are stack-independent:
`brainstorming` before features, `writing-plans` → `executing-plans` for
multi-step work, `systematic-debugging` for defects, and
`verification-before-completion` before claiming done.

## SITUATIONAL — load when the work calls for it

| Skill | Trigger |
|---|---|
| `api-connector-builder` | Adding a data source to `core/integrations/sources/` |
| `e2e-testing` | Touching the Playwright suite or the `e2e` marker |
| `accessibility` / `frontend-a11y` | Template or CSS work; the Lighthouse gate is advisory and a11y has never been audited |
| `security-review` | Auth, user data, or a new external call |
| `product-lens` / `product-capability` | Shaping a feature before it becomes tasks |
| `refactor-clean` | `core/views/__init__.py` (4,315 lines) and `core/api_views.py` (2,458) |
| `benchmark` | Integration suite runs 12m33s locally; it is the CI long pole |

## LIBRARY — reachable, never loaded by default

Off-stack by evidence, not by preference. Do not load without a concrete reason:

- **Languages/frameworks absent here:** TypeScript, React, Vue, Nuxt, Angular,
  Next, Kotlin, Swift, Flutter/Dart, Go, Rust, Java, C#, F#, C++, PHP/Laravel,
  Perl, ArkTS — and every matching `*-reviewer` and `*-build-resolver`
- **Domains absent here:** healthcare/EMR/HIPAA, networking and homelab,
  `ito-*`, DeFi / prediction markets / EVM, scientific databases, marketing
- **Infrastructure absent here:** Kubernetes, Celery, Redis, Prisma, MySQL,
  FastAPI, NestJS, Spring Boot, Quarkus, Supabase

That exclusion list is most of the catalog. Keeping it out is the point of this
file.

## Notes

- `ufawkesobs-observability` may be partly adopted already — `django-structlog`
  is a dependency and `docs/archive/UFAWKES_OBS_SETUP.md` exists. Confirm or
  retire it rather than leaving it ambiguous.
- Skills are guidance, not authority. Where an external skill conflicts with
  `AGENTS.md` or a sibling pack in `.agents/skills/`, the repo wins.
