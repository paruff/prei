# static/js

## Overview
Plain browser scripts, each an IIFE with no build step.

## Interface
- theme.js: light/dark/system toggle; elements `#theme-toggle`, `#theme-label`; persists to localStorage key `prei-theme`.
- notifications.js: notification bell (`#notificationBell`, `#notificationUnreadBadge`, `#notificationDropdown`, `#notificationList`, `#notificationConnectionStatus`); fetches `/api/v1/notifications`, marks items read, reconnects with backoff (5s initial, 60s max) and a 30s heartbeat; sends the CSRF cookie.

## Invariants
- Theme values limited to light, dark, system; default system.
- Notification text goes through `escapeHtml` before rendering.

## Side Effects
- localStorage read/write (storage errors are caught); HTTP calls to the notifications API; DOM updates.

## Verification
- No JS test runner is configured; page behaviour is covered by `.venv/bin/python -m pytest <paths>` where present.
