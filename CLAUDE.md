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
.claude/skills/                   — Claude Code skills (deploy-ha, verify-ha)
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
- Use `/deploy-ha` skill for quick deploy-verify cycles
- Use `/verify-ha` skill to check running integration status
- **NEVER** `kubectl delete pod homeassistant-0` — the InitContainer would overwrite copied files

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
