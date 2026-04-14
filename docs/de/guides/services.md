# Services

Die Integration stellt 5 Services bereit, die in Automationen, Scripts und der Entwicklerkonsole verwendbar sind.

---

## `kamerplanter.fill_tank`

Erfasst ein Tank-Fuell-Event. Dosierungen werden automatisch aus dem aktuellen Naehrplan aufgeloest.

```yaml
service: kamerplanter.fill_tank
data:
  entity_id: sensor.kp_90639_info
  fill_type: full_change
  measured_ec_ms: 1.8
  measured_ph: 6.2
  notes: "Bloom Week 5 Mix"
```

| Parameter | Pflicht | Beschreibung |
|-----------|---------|-------------|
| `entity_id` | Ja | Tank-Info-Sensor |
| `fill_type` | Ja | `full_change`, `top_up` oder `adjustment` |
| `volume_liters` | Nein | Fuellmenge in Litern |
| `measured_ec_ms` | Nein | Gemessener EC-Wert (mS/cm) |
| `measured_ph` | Nein | Gemessener pH-Wert |
| `notes` | Nein | Freitext-Notiz zum Fuell-Event |

---

## `kamerplanter.water_channel`

Erfasst ein Giessereignis fuer einen Duengekanal. Dosierungen und Volumen werden aus dem Naehrplan aufgeloest.

```yaml
service: kamerplanter.water_channel
data:
  entity_id: sensor.kp_12345_giesswasser_mix
  volume_liters: 2.5
  application_method: drench
  measured_ec_ms: 1.6
  measured_ph: 6.0
  notes: "Leichter Runoff"
```

| Parameter | Pflicht | Beschreibung |
|-----------|---------|-------------|
| `entity_id` | Ja | Mix-Sensor des Kanals |
| `volume_liters` | Nein | Giessmenge in Litern |
| `application_method` | Nein | `drench`, `foliar`, `fertigation` oder `capillary` |
| `measured_ec_ms` | Nein | Gemessener EC-Wert (mS/cm) |
| `measured_ph` | Nein | Gemessener pH-Wert |
| `notes` | Nein | Freitext-Notiz zum Giessereignis |

!!! tip "Application Method"
    Die Applikationsmethode beeinflusst, wie das Backend die Duengermengen berechnet. `drench` ist der Standard fuer normales Giessen, `foliar` fuer Blattduengung.

---

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

!!! example "In Kombination mit Actionable Notification"
    Siehe [Automationen: Actionable Care Notification](automations.md#actionable-care-notification) fuer ein vollstaendiges Beispiel.

---

## `kamerplanter.refresh_data`

Erzwingt erneutes Polling aller 5 Coordinatoren. Nuetzlich nach manuellen Aenderungen im Kamerplanter-Backend.

```yaml
service: kamerplanter.refresh_data
```

---

## `kamerplanter.clear_cache`

Leert den Coordinator-Cache und erzwingt vollstaendigen Neuaufbau aller Daten.

```yaml
service: kamerplanter.clear_cache
```

!!! warning "Cache leeren"
    Dieser Service entfernt alle gecachten Daten und laedt alles neu vom Backend. Verwende ihn nur bei Datenproblemen — im Normalbetrieb reicht `refresh_data`.
