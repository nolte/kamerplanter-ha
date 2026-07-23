# CLAUDE.md — kamerplanter-ha

This file provides guidance to Claude Code when working with the Kamerplanter Home Assistant Custom Integration.

## What This Repository Is

Dedicated repository for the **Kamerplanter Home Assistant Custom Integration** (HACS-compatible). Connects Home Assistant to a running [Kamerplanter](https://github.com/nolte/kamerplanter) backend instance.

The Kamerplanter backend lives in a separate repository: `/home/nolte/repos/github/kamerplanter/`

## Repository Structure

```
custom_components/kamerplanter/   — HA Custom Integration (Python)
  www/                            — Custom Lovelace Cards (vanilla JS)
  brand/                          — Brand assets (icon, logo)
  translations/                   — HA translations (de, en)
tests/                            — pytest tests (pytest-homeassistant-custom-component)
spec/ha-integration/              — HA integration specifications
spec/style-guides/                — HA integration style guide
.claude/agents/                   — Claude Code agents
# HA deploy/verify/provision tooling ships via the claude-home-assistant plugin, not as project skills
.github/workflows/                — CI (lint, test, hassfest, release)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ (HA compatibility, not 3.14+ like backend) |
| Framework | Home Assistant Core (DataUpdateCoordinator, ConfigEntry, Entity Registry) |
| HTTP Client | aiohttp (HA built-in) |
| Cards | Vanilla JS (HTMLElement + Shadow DOM) |
| Testing | pytest + pytest-homeassistant-custom-component |
| Linting | Ruff |
| CI | GitHub Actions + HACS Action |

## Verbindliche Style Guides

All code MUST follow:
- **HA Integration:** `spec/style-guides/HA-INTEGRATION.md` — runtime_data, Base Entity, EntityDescription, translations, Config Flow, Coordinator, API-Client, Custom Cards

## Key Patterns

1. **runtime_data** — No `hass.data[DOMAIN]` dict; use `entry.runtime_data` typed dataclass
2. **EntityDescription** — No individual entity classes per data point; use description-based pattern
3. **Entity IDs** — Never set `self.entity_id` manually; HA generates from `has_entity_name` + `translation_key`
4. **Translations** — All strings via `strings.json` + `translations/`; icons via `icons.json`
5. **DeviceInfo** — All devices link to server hub via `via_device`
6. **Coordinator** — Separate coordinators for plants, locations, alerts, tasks with configurable intervals
7. **Cards** — Entity-change-detection mandatory; no `set hass()` without diff check

## Development Workflow

- **Deploy to local Kind cluster** via `kubectl cp` + container restart (NOT pod delete)
- Provision a dev HA instance with the `claude-home-assistant:ha-dev-instance-provision` agent
- Deploy / verify the integration with the `claude-home-assistant:ha-integration-deploy` and
  `claude-home-assistant:ha-integration-verify` agents (provided by the plugin, not project skills)
- The `Taskfile.yml` `deploy-ha` / `verify-ha` targets remain as manual entry points
- **NEVER** `kubectl delete pod homeassistant-0` to refresh code — use `kill 1` (container restart);
  deleting the pod re-runs the init container and overwrites the copied files

## Backend Reference

The Kamerplanter backend API is the data source. For API sync tasks, the backend code lives at:
`/home/nolte/repos/github/kamerplanter/src/backend/`

Key backend paths for reference (read-only):
- `src/backend/app/api/v1/*/router.py` — Feature routers (global)
- `src/backend/app/api/v1/*/tenant_router.py` — Tenant-scoped routers
- `src/backend/app/api/v1/*/schemas.py` — Pydantic response schemas

## Code Language

Source code MUST be in **English** (variable names, class names, function names, strings.json keys).
Documentation and comments may be in German.

## Documentation Conventions

- **Anrede (DE docs):** The German documentation under `docs/de/` deliberately uses the
  informal **"du"** address throughout — including on `reference` pages — to match the
  Home-Assistant hobbyist audience. This is an intentional house-style override of the
  generic lektorat "Sie"/impersonal rule; lektorat findings that flag "du" on how-to or
  reference pages are expected and should not be "fixed".
- **Coordinator plural (DE):** use the loanword form **"Coordinators"** (not "Coordinatoren")
  consistently across the docs.
