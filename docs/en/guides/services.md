---
title: Services
audience:
  - ha-end-users
  - self-hosting-admin
content_mode: reference
track: user-docs
last_updated: 2026-06-24
---
# Services

The integration provides 5 services. Use these services in automations, scripts, and the developer console.

---

## `kamerplanter.fill_tank`

Records a tank fill event. The service resolves current dosages from the nutrient plan.

```yaml
service: kamerplanter.fill_tank
data:
  entity_id: sensor.kp_90639_info
  fill_type: full_change
  measured_ec_ms: 1.8
  measured_ph: 6.2
  notes: "Bloom Week 5 Mix"
```

| Parameter | Required | Description |
|-----------|----------|------------|
| `entity_id` | Yes | Tank info sensor |
| `fill_type` | Yes | `full_change`, `top_up`, or `adjustment` |
| `volume_liters` | No | Fill volume in liters |
| `measured_ec_ms` | No | Measured EC (electrical conductivity) value (mS/cm) |
| `measured_ph` | No | Measured pH value |
| `notes` | No | Free-text note for the fill event |

---

## `kamerplanter.water_channel`

Records a watering event for a delivery channel. The service resolves dosages and volume from the nutrient plan.

```yaml
service: kamerplanter.water_channel
data:
  entity_id: sensor.kp_12345_giesswasser_mix
  volume_liters: 2.5
  application_method: drench
  measured_ec_ms: 1.6
  measured_ph: 6.0
  notes: "Light runoff"
```

| Parameter | Required | Description |
|-----------|----------|------------|
| `entity_id` | Yes | Channel mix sensor |
| `volume_liters` | No | Watering volume in liters |
| `application_method` | No | `drench`, `foliar`, `fertigation`, or `capillary` |
| `measured_ec_ms` | No | Measured EC value (mS/cm) |
| `measured_ph` | No | Measured pH value |
| `notes` | No | Free-text note for the watering event |

!!! tip "Application method"
    The application method affects how the backend calculates fertilizer amounts. Use `drench` for normal watering. Use `foliar` for foliar feeding.

---

## `kamerplanter.confirm_care`

Confirms or skips a care reminder. It targets actionable notifications via the HA Companion App.

!!! info "Actionable notifications"
    These are interactive notifications with response buttons. You tap an action directly in the notification.

```yaml
service: kamerplanter.confirm_care
data:
  notification_key: "notif_20260321_abc123"
  action: confirmed
```

| Parameter | Required | Description |
|-----------|----------|------------|
| `notification_key` | Yes | Notification key |
| `action` | Yes | `confirmed` or `skipped` |

!!! example "With actionable notification"
    See [Automations: Actionable Care Notification](automations.md#actionable-care-notification) for a complete example.

---

## `kamerplanter.refresh_data`

Forces a re-poll of all six coordinators. Use it after manual changes in the Kamerplanter backend.

```yaml
service: kamerplanter.refresh_data
```

---

## `kamerplanter.clear_cache`

Clears the coordinator cache. This forces a full rebuild of all data from the backend.

```yaml
service: kamerplanter.clear_cache
```

!!! warning "Cache clearing"
    This service removes all cached data and reloads everything from the backend. Only use it for data issues. In normal operation, `refresh_data` is sufficient.
