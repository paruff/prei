# Real Estate Investor — Property Analytics

A Django-based web application to analyze and track residential real estate investments (KPIs such as Cash-on-Cash, Cap Rate, NOI, IRR, DSCR, etc.). This repository contains the initial scaffold and CI for building the investment analytics web app.

## ✨ Features

- **Investment Analysis**: Calculate financial KPIs (Cash-on-Cash, Cap Rate, NOI, IRR, DSCR)
- **Foreclosure Property Data**: Access foreclosure listings with detailed property information
- **Real-Time Auction Monitoring**: WebSocket-based live updates for auction status changes
- **Smart Alerts**: Configure custom alerts based on location, price range, and property type
- **Watchlists**: Track specific properties of interest
- **In-App Notifications**: Receive real-time notifications for auction updates and reminders

## 📚 Documentation

Comprehensive documentation is available at **[https://paruff.github.io/prei/](https://paruff.github.io/prei/)**

The documentation follows the [Diátaxis framework](https://diataxis.fr/) with four sections:
- **[Tutorials](https://paruff.github.io/prei/tutorials/getting-started/)** — Step-by-step learning guides
- **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** — Practical solutions for specific tasks
- **[Reference](https://paruff.github.io/prei/reference/)** — Technical specifications and API docs
- **[Explanation](https://paruff.github.io/prei/explanation/)** — Architecture and design rationale

To build documentation locally:
```bash
pip install -r docs-requirements.txt
mkdocs serve  # View at http://127.0.0.1:8000
```

## Quick start (local)

For detailed setup instructions, see the **[Getting Started Tutorial](https://paruff.github.io/prei/tutorials/getting-started/)**.

1. Clone the repo:
   - `git clone git@github.com:paruff/prei.git`
   - `cd prei`

2. Create a virtual environment and install deps:
   - `python3.11 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`

3. Create .env from .env.example and update values:
   - `cp .env.example .env`
   - Edit `.env` (set SECRET_KEY, DATABASE_URL)

4. Run migrations and start dev server:
   - `python manage.py migrate`
   - `python manage.py runserver`

## Quick start (Codespaces / Dev Container)

If you open this repository in a GitHub Codespace or VS Code Dev Container, use the devcontainer as the development runtime instead of trying to run Docker Compose inside the container.

1. Open the repository in the devcontainer.
   - The devcontainer starts `web` and `db` from [.devcontainer/docker-compose.yml](./.devcontainer/docker-compose.yml).
   - Dependencies are installed automatically by [.devcontainer/devcontainer.json](./.devcontainer/devcontainer.json).

2. Initialize the app in the integrated terminal:
   - `make dev`

   In a second terminal, create a superuser the first time only:
   - `python manage.py createsuperuser`

3. Open the forwarded port for `8000`.
   - Web: `http://localhost:8000`
   - Admin: `http://localhost:8000/admin`

This is the fastest workflow for rapid development because the database already runs as a sidecar container and code changes apply immediately from the mounted workspace.

Available convenience targets:
- `make dev` runs migrations and starts the Django development server.
- `make superuser` creates an admin user in the current environment.
- `make lint` runs Ruff and Black checks.
- `make test` runs `pytest -q`.
- `make check` runs `manage.py check`, lint, and tests.
- `make deploy-dev` starts the image-based Docker stack when Docker is available.

## Quick start (Docker host deployment)

Use the root compose file when you want to run the published container image on a machine that has Docker available.

1. Create `.env` from `.env.example` and set required values.
   - At minimum set `POSTGRES_PASSWORD`.

2. Start the stack from the repository root:
   - `docker compose up -d`

3. Create a superuser if needed:
   - `docker compose exec web python manage.py createsuperuser`

Notes:
- The root [docker-compose.yml](./docker-compose.yml) uses `image: ghcr.io/paruff/prei:latest`; it does not build the application image locally.
- Published images default `RUN_MIGRATIONS=1`, so they run `python manage.py migrate --noinput` during container startup before Gunicorn begins serving requests.
- For multi-replica or rolling deployments, set `RUN_MIGRATIONS=0` on replicas that should not apply migrations.
- Run migrations from a dedicated one-shot instance/job instead of every replica, for example:
  `docker run --rm --env-file .env ghcr.io/paruff/prei:latest python manage.py migrate`
- The published image sets `HOME` and `MPLCONFIGDIR` to a dedicated writable runtime directory owned by the app user.
- Container healthchecks allow extra startup time for pre-start migration work before marking the service unhealthy.
- If you want to build locally from the repository source, use the root [Dockerfile](./Dockerfile): `docker build -t prei:dev .`
- Modern Docker uses `docker compose`; the legacy `docker-compose` binary may not be installed.
- In a Codespace or VS Code Dev Container, rebuild the container after changes to [.devcontainer/devcontainer.json](./.devcontainer/devcontainer.json) if you want the `docker` CLI available inside the workspace container.

## Real-Time Auction Monitoring

The application includes a real-time auction monitoring system with the following capabilities:

### WebSocket Connection

Connect to the WebSocket endpoint at `ws://localhost:8000/ws/auctions/` to receive real-time updates:

```javascript
const socket = new WebSocket('ws://localhost:8000/ws/auctions/');

socket.onopen = () => {
  console.log('Connected to auction updates');
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

// Subscribe to a property
socket.send(JSON.stringify({
  type: 'subscribe',
  propertyId: '123'
}));

// Heartbeat
setInterval(() => {
  socket.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

### API Endpoints

**Watchlist Management:**
- `GET /api/v1/watchlist` - List watched properties
- `POST /api/v1/watchlist` - Add property to watchlist
- `DELETE /api/v1/watchlist/{id}` - Remove from watchlist

**Alert Configuration:**
- `GET /api/v1/alerts` - List user's alerts
- `POST /api/v1/alerts` - Create new alert
- `GET /api/v1/alerts/{id}` - Get alert details
- `PUT /api/v1/alerts/{id}` - Update alert
- `DELETE /api/v1/alerts/{id}` - Delete alert

**Notifications:**
- `GET /api/v1/notifications` - List notifications
- `POST /api/v1/notifications/{id}/read` - Mark as read
- `POST /api/v1/notifications/{id}/dismiss` - Dismiss notification

**Notification Preferences:**
- `GET /api/v1/notification-preferences` - Get preferences
- `PUT /api/v1/notification-preferences` - Update preferences

### Alert Configuration Example

```json
{
  "name": "California Auctions",
  "alertType": "new_auction",
  "isActive": true,
  "states": ["CA", "NV"],
  "minOpeningBid": "200000.00",
  "maxOpeningBid": "500000.00",
  "radiusMiles": 50,
  "centerLatitude": "34.0522",
  "centerLongitude": "-118.2437"
}
```

### Background Tasks

Celery tasks run periodically:
- **Auction Monitoring**: Checks for status changes every 15 minutes
- **Auction Reminders**: Sends reminders at 7 days, 3 days, 1 day, and 1 hour before auction

## CI & tooling

- **Linting & formatting:** ruff + black
- **Type checking:** mypy (encouraged for new modules)
- **Tests:** pytest + Django testing tools
- **Documentation:** MkDocs with Material theme
- **CI:** GitHub Actions (see `.github/workflows/`) — workflows include DORA-friendly logging of deploy/test start/finish timestamps and commit SHA.

See the **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** for detailed instructions on running tests, linters, and other development tasks.

## Repository purpose

- Host the web application and all related code, tests, infra config, and documentation for the investment/analysis product.
- Keep the old scraper (if useful) in a standalone archival repo or in a `legacy-scraper/` directory only after explicit migration.

## Contributing

Please refer to our documentation for information on how to contribute to this project. See **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** and **[Explanation](https://paruff.github.io/prei/explanation/)** sections.

## License

This project is licensed under the terms specified in the repository.
