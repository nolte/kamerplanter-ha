# Changelog

## 0.1.0 (Initial Release)

### Integration

- Config flow with URL, API key, tenant selection
- Reauth flow (new API key) and reconfigure flow (change server URL)
- 5 coordinators (Plant, Location, Run, Alert, Task) with configurable polling intervals

### Entities

- Sensors for plants (phase, days in phase, VPD/EC targets, nutrient plan, watering)
- Sensors for runs (status, plant count, phase progression)
- Sensors for locations (type, active runs/plants, run phase)
- Sensors for tanks (info, volume, fill level)
- Server sensors (due/overdue tasks, next watering)
- Binary sensors (attention, care, sensor status)
- Calendar entities (phases, tasks)
- Todo entity with backend sync

### Services

- `fill_tank` — fill tank with EC/pH/notes
- `water_channel` — water channel with application method and measurements
- `confirm_care` — confirm/skip care reminder
- `refresh_data` — re-poll all coordinators
- `clear_cache` — clear coordinator cache

### Cards & UI

- 5 custom Lovelace cards (plant, mix, tank, care, houseplant)
- 11 event types for automations
- DE/EN translations
- Diagnostics
