# Services

The integration provides 5 services that can be used in automations, scripts, and the developer console.

---

## `kamerplanter.fill_tank`

Records a tank fill event. Automatically resolves current dosages from the nutrient plan.

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
| `measured_ec_ms` | No | Measured EC value (mS/cm) |
| `measured_ph` | No | Measured pH value |
| `notes` | No | Free-text note for the fill event |

---

## `kamerplanter.water_channel`

Records a watering event for a delivery channel. Resolves dosages and volume from the nutrient plan.

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
    The application method affects how the backend calculates fertilizer amounts. `drench` is the default for normal watering, `foliar` for foliar feeding.

---

## `kamerplanter.confirm_care`

Confirms or skips a care reminder. Designed for actionable notifications via the HA Companion App.

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

Force re-poll of all 5 coordinators. Useful after manual changes in the Kamerplanter backend.

```yaml
service: kamerplanter.refresh_data
```

---

## `kamerplanter.clear_cache`

Clear coordinator cache and force full rebuild of all data.

```yaml
service: kamerplanter.clear_cache
```

!!! warning "Cache clearing"
    This service removes all cached data and reloads everything from the backend. Only use it for data issues — in normal operation, `refresh_data` is sufficient.
