## Phase 4.4 — Team Collaboration: Shared Properties, Notes & Exports

### User Story
As an investment team, we want to share property analyses, leave notes, and export deal packs so that multiple team members can collaborate on the same deals without emailing spreadsheets.

### Background
- `Property` model is currently per-user (`user = ForeignKey(User, ...)`)
- No team or sharing model exists
- Export services exist in `core/export_services/` and `core/export_helpers.py`

### Acceptance Criteria
- [ ] Add models to `core/models.py`:
  - `Team` — `name`, `owner (FK User)`, `created_at`
  - `TeamMember` — `team (FK Team)`, `user (FK User)`, `role (choices: owner/member)`, `joined_at`
  - `PropertyNote` — `property (FK Property)`, `author (FK User)`, `body (TextField)`, `created_at`
  - `SharedProperty` — `property (FK Property)`, `team (FK Team)`, `shared_by (FK User)`, `shared_at`
- [ ] Create migrations for all new models
- [ ] Add `core/services/collaboration.py` with:
  - `share_property_with_team(property: Property, team: Team, shared_by: User) -> SharedProperty`
  - `add_note(property: Property, author: User, body: str) -> PropertyNote`
  - `get_team_properties(team: Team) -> QuerySet[Property]` — returns all properties shared with the team
- [ ] Add export endpoint `GET /api/property/<id>/export/` that returns a JSON "deal pack":
  - Property details, KPIs (from `compute_analysis_for_property`), notes, market snapshot
- [ ] Unit tests in `core/tests/test_collaboration.py` (`@pytest.mark.django_db`):
  - `share_property_with_team` creates a `SharedProperty` record
  - `add_note` creates a `PropertyNote` with correct author
  - `get_team_properties` returns only properties shared with that team
  - Export endpoint returns 200 with all expected keys in JSON

### Files to Change
| File | Action |
|------|--------|
| `core/models.py` | **Edit** — add `Team`, `TeamMember`, `PropertyNote`, `SharedProperty` |
| `core/migrations/` | **Create** — migration |
| `core/services/collaboration.py` | **Create** |
| `core/api_views.py` | **Edit** — add property export endpoint |
| `core/api_urls.py` | **Edit** — register export URL |
| `core/tests/test_collaboration.py` | **Create** |

### Implementation Notes
- Permissions: only team members can access `get_team_properties` (check membership in service)
- `share_property_with_team` is idempotent — `update_or_create` on `(property, team)`
- Export endpoint requires authentication (`@login_required` or DRF permission)
- Migrations must be reversible

### Definition of Done
- `pytest core/tests/test_collaboration.py -v` passes
- Migrations apply and reverse cleanly
- `ruff check core/services/collaboration.py core/models.py` passes
- Export endpoint returns valid JSON deal pack (verified with test client)

### Labels
`enhancement` `phase-4` `backend`
