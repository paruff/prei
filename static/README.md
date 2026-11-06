# static

## Overview
Hand-written front-end assets served by Django: the custom design system (no Bootstrap), icons, fonts, a PWA
manifest and a service worker. `staticfiles/` is collected output and is gitignored.

## Subdirectories & Boundaries
- js: [./js/README.md](./js/README.md) - theme toggle and notification bell scripts.
- css, fonts, icons: assets only, no code contracts.
- `manifest.json`, `sw.js`: PWA manifest and service worker (not covered by a contract).
