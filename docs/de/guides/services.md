# Services

## `kamerplanter.fill_tank`

Erfasst ein Tank-Fuell-Event. Dosierungen werden automatisch aus dem Naehrplan aufgeloest.

```yaml
service: kamerplanter.fill_tank
data:
  entity_id: sensor.kp_90639_info
  fill_type: full_change
  measured_ec_ms: 1.8
  measured_ph: 6.2
```

| Parameter | Pflicht | Beschreibung |
|-----------|---------|-------------|
| `entity_id` | Ja | Tank-Info-Sensor |
| `fill_type` | Ja | `full_change` oder `top_up` |
| `volume_liters` | Nein | Fuellmenge in Litern |
| `measured_ec_ms` | Nein | Gemessener EC-Wert |
| `measured_ph` | Nein | Gemessener pH-Wert |

## `kamerplanter.water_channel`

Erfasst ein Giessereignis fuer einen Duengekanal. Dosierungen und Volumen werden aus dem Naehrplan aufgeloest.

```yaml
service: kamerplanter.water_channel
data:
  entity_id: sensor.kp_12345_giesswasser_mix
  volume_liters: 2.5
```

| Parameter | Pflicht | Beschreibung |
|-----------|---------|-------------|
| `entity_id` | Ja | Mix-Sensor des Kanals |
| `volume_liters` | Nein | Giessmenge in Litern |

## `kamerplanter.confirm_care`

Bestaetigt oder ueberspringt eine Pflege-Erinnerung. Fuer Actionable Notifications via HA Companion App.

```yaml
service: kamerplanter.confirm_care
data:
  notification_key: "notif_20260321_abc123"
  action: confirmed
```

| Parameter | Pflicht | Beschreibung |
|-----------|---------|-------------|
| `notification_key` | Ja | Key der Benachrichtigung |
| `action` | Ja | `confirmed` oder `skipped` |

## `kamerplanter.refresh_data`

Erzwingt erneutes Polling aller Coordinatoren.

```yaml
service: kamerplanter.refresh_data
```

## `kamerplanter.clear_cache`

Leert den Coordinator-Cache und erzwingt vollstaendigen Neuaufbau.

```yaml
service: kamerplanter.clear_cache
```
