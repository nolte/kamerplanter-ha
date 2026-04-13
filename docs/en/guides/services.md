# Services

## `kamerplanter.fill_tank`

Records a tank fill event. Automatically resolves current dosages from the nutrient plan.

```yaml
service: kamerplanter.fill_tank
data:
  entity_id: sensor.kp_90639_info
  fill_type: full_change
  measured_ec_ms: 1.8
  measured_ph: 6.2
```

| Parameter | Required | Description |
|-----------|----------|------------|
| `entity_id` | Yes | Tank info sensor |
| `fill_type` | Yes | `full_change` or `top_up` |
| `volume_liters` | No | Fill volume in liters |
| `measured_ec_ms` | No | Measured EC value |
| `measured_ph` | No | Measured pH value |

## `kamerplanter.water_channel`

Records a watering event for a delivery channel. Resolves dosages and volume from the nutrient plan.

```yaml
service: kamerplanter.water_channel
data:
  entity_id: sensor.kp_12345_giesswasser_mix
  volume_liters: 2.5
```

| Parameter | Required | Description |
|-----------|----------|------------|
| `entity_id` | Yes | Channel mix sensor |
| `volume_liters` | No | Watering volume in liters |

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

## `kamerplanter.refresh_data`

Force re-poll of all coordinators.

```yaml
service: kamerplanter.refresh_data
```

## `kamerplanter.clear_cache`

Clear coordinator cache and force full rebuild.

```yaml
service: kamerplanter.clear_cache
```
