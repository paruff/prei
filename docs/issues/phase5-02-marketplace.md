## Phase 5.2 — Marketplace Models & Views

### User Story
As an investor, I want a marketplace where I can connect with agents, lenders, and contractors so that I can close deals faster with trusted professionals.

### Background
- `Property` and `User` models exist
- No marketplace models exist today
- Django auth groups can be used for roles

### Acceptance Criteria
- [ ] Add models to `core/models.py`:
  - `MarketplaceProfile` — `user (OneToOne)`, `role (choices: agent/lender/contractor/investor)`, `bio (TextField)`, `phone`, `website`, `is_verified (bool, default False)`, `rating (DecimalField 1–5, null)`, `created_at`
  - `MarketplaceReview` — `reviewer (FK User)`, `profile (FK MarketplaceProfile)`, `rating (PositiveSmallIntegerField 1–5)`, `comment (TextField)`, `created_at`; unique on `(reviewer, profile)`
- [ ] Create migrations for both models
- [ ] Add views and URLs:
  - `GET /marketplace/` — list all verified profiles, filterable by `role`
  - `GET /marketplace/profile/<id>/` — profile detail with reviews and average rating
  - `POST /marketplace/profile/<id>/review/` — submit a review (authenticated users only; one review per reviewer per profile)
- [ ] Add templates:
  - `templates/marketplace_list.html`
  - `templates/marketplace_profile.html`
- [ ] Unit / integration tests in `core/tests/test_marketplace.py` (`@pytest.mark.django_db`):
  - Marketplace list returns only verified profiles
  - Unverified profile not shown in list
  - Submitting a review creates `MarketplaceReview` and updates average rating
  - Duplicate review → 400 or redirect with error
  - Unauthenticated review POST → 302 to login

### Files to Change
| File | Action |
|------|--------|
| `core/models.py` | **Edit** — add `MarketplaceProfile`, `MarketplaceReview` |
| `core/migrations/` | **Create** — migration |
| `core/views.py` | **Edit** — add marketplace list, detail, review views |
| `core/urls.py` | **Edit** — register marketplace URLs |
| `templates/marketplace_list.html` | **Create** |
| `templates/marketplace_profile.html` | **Create** |
| `core/tests/test_marketplace.py` | **Create** |

### Implementation Notes
- Average rating: compute via `MarketplaceReview.objects.filter(profile=...).aggregate(Avg("rating"))`
- Moderation: `is_verified` is set manually (via admin) in Phase 5; no auto-verify
- `MarketplaceReview` `rating` must be between 1 and 5 — add a `MinValueValidator(1)` and `MaxValueValidator(5)`
- All views must use `@login_required` for write operations

### Definition of Done
- `pytest core/tests/test_marketplace.py -v` passes
- Migrations apply and reverse cleanly
- `ruff check core/views.py core/models.py` passes
- Marketplace list page renders (screenshot in PR)

### Labels
`enhancement` `phase-5` `backend` `frontend`
