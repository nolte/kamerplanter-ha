---
title: Changelog
audience:
  - ha-end-users
  - self-hosting-admin
  - maintainers
content_mode: meta
track: user-docs
last_updated: 2026-07-23
---
# Changelog

## 0.1.6

### Added

- **Frost warning:** new Weather coordinator with a proactive per-site frost-forecast sensor (`binary_sensor.kp_site_{key}_frost_forecast`)
- **Interactive task card** with start / complete / skip actions
- Three new services: `start_task`, `complete_task`, `skip_task`
- Section visibility toggles for cards, redesigned day badge

### Fixed

- The care card now shows live tasks and the concrete care activity instead of a static preview
- Contained card overflow and tightened density in sections view
- Restricted the device picker to plant / run devices; human-readable plant names instead of code slugs
- Published tanks appear as HA devices regardless of location publishing
- Lovelace YAML resource mode now surfaces via a repair issue instead of failing silently

### Other

- Added MIT license

## 0.1.5

Maintenance release: release-automation and CI changes only, no functional changes to the integration.

## 0.1.4

### Added

- **IPM entities** (Integrated Pest Management): pest pressure, waiting period, and harvest safety as sensors plus pest / harvest-safe binary sensors
- **mDNS / Zeroconf auto-discovery:** backends advertising `_kamerplanter._tcp.local.` are discovered automatically
- Opt-in filter for the objects published to Home Assistant
- Compact 2-column grid layout across all cards
- Added `AUDIENCES.md` and the portfolio manifest

## 0.1.3

Maintenance release: docs deploy moved to a release-triggered workflow.

## 0.1.2

Maintenance release: CI workflows for release automation and automerge.

## 0.1.1

Maintenance release: release-drafter workflow; closed documentation gaps and restyled with mkdocs-material.

## 0.1.0 (Initial Release)

### Integration

- Config flow with URL, API key, tenant selection
- Reauth flow (new API key) and reconfigure flow (change server URL)
- 5 coordinators (Plant, Location, Run, Alert, Task) with configurable polling intervals

### Entities

- Sensors for plants (phase, days in phase, nutrient plan, watering)
- Sensors for runs (status, plant count, phase progression)
- Sensors for locations (type, active runs/plants, run phase)
- Sensors for tanks (info, volume)
- Server sensors (due/overdue tasks, next watering)
- Binary sensors (attention, care, sensor status)
- Calendar entities (phases, tasks)
- Todo entity with backend sync

### Services

- `fill_tank` — fill tank with EC (electrical conductivity)/pH/notes
- `water_channel` — water channel with application method and measurements
- `confirm_care` — confirm/skip care reminder
- `refresh_data` — re-poll all coordinators
- `clear_cache` — clear coordinator cache

### Cards & UI

- 5 custom Lovelace cards (plant, mix, tank, care, houseplant)
- 11 event types for automations
- DE/EN translations
- Diagnostics
