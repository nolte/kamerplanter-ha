<p align="center">
  <img src="https://raw.githubusercontent.com/nolte/kamerplanter-ha/main/docs/assets/images/banner-ha-integration.png" alt="Kamerplanter Home Assistant Integration" />
</p>

# Kamerplanter Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![HA Version](https://img.shields.io/badge/HA-2024.1.0+-blue.svg)](https://www.home-assistant.io/)

Custom Integration for [Home Assistant](https://www.home-assistant.io/) to connect your [Kamerplanter](https://github.com/nolte/kamerplanter) plant management system.

## Features

- **Plant monitoring** — growth phases, days in phase, next phase predictions, nutrient plan assignments
- **Nutrient dosages** — per-channel mixing ratios (ml/L) as sensor attributes, ready for dashboard cards
- **Tank management** — fill events, solution age, EC/pH tracking via HA services
- **Location overview** — active runs and plant counts per tent, room, or bed
- **Task tracking** — todo list entity, overdue counts, calendar events for phases and tasks
- **Care reminders** — binary sensors for overdue care, events for actionable notifications
- **5 custom Lovelace cards** — plant card, mix card, tank card, care card, houseplant card (auto-registered)
- **Services** — fill tank, water channel, confirm care, refresh data, clear cache

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots (top right) and select **Custom repositories**
3. Add `https://github.com/nolte/kamerplanter-ha` with category **Integration**
4. Search for **Kamerplanter** and click **Download**
5. Restart Home Assistant

### Manual

1. Download the [latest release](https://github.com/nolte/kamerplanter-ha/releases/latest)
2. Extract and copy `custom_components/kamerplanter/` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings > Devices & Services > Add Integration > Kamerplanter**
2. Enter the URL of your Kamerplanter instance (e.g. `http://kamerplanter-backend:8000`)
3. Enter your API key (format `kp_...`) — optional in Light Mode
4. Select your tenant (auto-selected if only one exists)

### Polling intervals

Configurable under **Settings > Devices & Services > Kamerplanter > Configure**:

| Option | Default | Minimum | Description |
|--------|---------|---------|-------------|
| Plants | 300s | 120s | Plant instances, phases, dosages |
| Locations | 300s | 120s | Sites, tanks, runs |
| Alerts | 60s | 30s | Overdue tasks, sensor offline |
| Tasks | 300s | 120s | Pending tasks |

## Entities

### Sensors

**Per plant instance:**
`sensor.kp_{key}_phase`, `_days_in_phase`, `_nutrient_plan`, `_phase_timeline`, `_next_phase`, `_active_channels`, `_{channel}_mix`

**Per planting run:**
`sensor.kp_{key}_status`, `_plant_count`, `_nutrient_plan`, `_phase_timeline`, `_next_phase`, `_{channel}_mix`

**Per location:**
`sensor.kp_loc_{key}_type`, `_active_run_count`, `_active_plant_count`, `_run_phase`, `_run_days_in_phase`, `_run_nutrient_plan`, `_run_next_phase`, `_{channel}_mix`

**Per tank:**
`sensor.kp_{key}_info`, `_volume`

**Server:**
`sensor.kp_tasks_due_today`, `_tasks_overdue`, `_next_watering`

### Binary sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.kp_{key}_needs_attention` | Plant has overdue tasks |
| `binary_sensor.kp_loc_{key}_needs_attention` | Location has overdue tasks |
| `binary_sensor.kp_sensor_offline` | At least one sensor is offline |
| `binary_sensor.kp_care_overdue` | Care tasks overdue (attribute: `overdue_count`) |

### Calendar, Todo, Button

| Entity | Description |
|--------|-------------|
| `calendar.kp_phases` | Growth phases as multi-day events |
| `calendar.kp_tasks` | Pending tasks with due dates |
| `todo.kp_tasks` | Task list — checking off marks tasks as done in the backend |
| `button.kp_refresh_all` | Manual refresh of all coordinators |

## Services

### `kamerplanter.fill_tank`

Records a tank fill event. Automatically resolves current dosages from the nutrient plan.

```yaml
service: kamerplanter.fill_tank
data:
  entity_id: sensor.kp_90639_info
  fill_type: full_change
  measured_ec_ms: 1.8
  measured_ph: 6.2
```

### `kamerplanter.water_channel`

Records a watering event for a delivery channel. Resolves dosages and volume from the nutrient plan.

```yaml
service: kamerplanter.water_channel
data:
  entity_id: sensor.kp_12345_giesswasser_mix
  volume_liters: 2.5
```

### `kamerplanter.confirm_care`

Confirms or skips a care reminder. Designed for actionable notifications via the HA Companion App.

```yaml
service: kamerplanter.confirm_care
data:
  notification_key: "notif_20260321_abc123"
  action: confirmed
```

### `kamerplanter.refresh_data` / `kamerplanter.clear_cache`

Force re-poll or clear coordinator cache.

## Automation examples

**Tank refill on low level:**
```yaml
automation:
  trigger:
    - platform: numeric_state
      entity_id: sensor.kp_90639_fill_level
      below: 20
  action:
    - service: kamerplanter.fill_tank
      data:
        entity_id: sensor.kp_90639_info
        fill_type: top_up
        volume_liters: 30
```

**Daily watering with attention check:**
```yaml
automation:
  trigger:
    - platform: time
      at: "08:00:00"
  condition:
    - condition: state
      entity_id: binary_sensor.kp_12345_needs_attention
      state: "on"
  action:
    - service: kamerplanter.water_channel
      data:
        entity_id: sensor.kp_12345_giesswasser_mix
```

**Actionable care notification:**
```yaml
automation:
  trigger:
    - platform: event
      event_type: kamerplanter_care_due
  action:
    - service: notify.mobile_app_phone
      data:
        title: "Care due"
        message: "{{ trigger.event.data.message }}"
        data:
          actions:
            - action: "CONFIRM_CARE_{{ trigger.event.data.notification_key }}"
              title: "Done"
            - action: "SKIP_CARE_{{ trigger.event.data.notification_key }}"
              title: "Skip"
```

## Events

| Event | Description |
|-------|-------------|
| `kamerplanter_task_completed` | Task checked off via todo entity |
| `kamerplanter_data_refreshed` | Manual refresh via button |
| `kamerplanter_care_due` | Care reminder due |
| `kamerplanter_phase` | Phase transition |
| `kamerplanter_tank_alert` | Tank alert (low level, old solution) |
| `kamerplanter_harvest` | Harvest notification |
| `kamerplanter_ipm_alert` | Pest/disease alert |
| `kamerplanter_sensor_alert` | Sensor offline/threshold |
| `kamerplanter_task_due` | Task due |
| `kamerplanter_weather_alert` | Weather warning |
| `kamerplanter_seasonal` | Seasonal reminder |

## Custom Lovelace cards

The integration ships with 5 custom cards that are auto-registered on setup:

| Card | Description |
|------|-------------|
| `kamerplanter-plant-card` | Plant instance overview with phase timeline |
| `kamerplanter-mix-card` | Nutrient dosage visualization per channel |
| `kamerplanter-tank-card` | Tank status with fill level and solution age |
| `kamerplanter-care-card` | Care reminders with confirm/skip actions |
| `kamerplanter-houseplant-card` | Simplified card for houseplant monitoring |

Cards are served from the integration's `www/` directory — no manual resource registration needed.

## Links

- [Kamerplanter Documentation](https://nolte.github.io/kamerplanter/)
- [Issues](https://github.com/nolte/kamerplanter-ha/issues)
- [Releases](https://github.com/nolte/kamerplanter-ha/releases)
