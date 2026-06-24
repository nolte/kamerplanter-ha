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

Die Integration stellt 5 Services bereit. Nutze diese Services in Automationen, Scripts und der Entwicklerkonsole.

---

## `kamerplanter.fill_tank`

Erfasst ein Tank-Füll-Event. Der Service löst die Dosierungen aus dem aktuellen Nährplan auf.

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
| `volume_liters` | Nein | Füllmenge in Litern |
| `measured_ec_ms` | Nein | Gemessener EC-Wert (elektrische Leitfähigkeit, mS/cm) |
| `measured_ph` | Nein | Gemessener pH-Wert |
| `notes` | Nein | Freitext-Notiz zum Füll-Event |

---

## `kamerplanter.water_channel`

Erfasst ein Gießereignis für einen Düngekanal. Der Service löst Dosierungen und Volumen aus dem Nährplan auf.

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
| `volume_liters` | Nein | Gießmenge in Litern |
| `application_method` | Nein | `drench`, `foliar`, `fertigation` oder `capillary` |
| `measured_ec_ms` | Nein | Gemessener EC-Wert (mS/cm) |
| `measured_ph` | Nein | Gemessener pH-Wert |
| `notes` | Nein | Freitext-Notiz zum Gießereignis |

!!! tip "Application Method"
    Die Applikationsmethode beeinflusst, wie das Backend die Düngermengen berechnet. Nutze `drench` für normales Gießen. Nutze `foliar` für Blattdüngung.

---

## `kamerplanter.confirm_care`

Bestätigt oder überspringt eine Pflege-Erinnerung. Der Service zielt auf Actionable Notifications über die HA Companion App.

!!! info "Actionable Notifications"
    Das sind interaktive Benachrichtigungen mit Antwort-Buttons. Du tippst direkt in der Benachrichtigung auf eine Aktion.

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
    Siehe [Automationen: Actionable Care Notification](automations.md#actionable-care-notification) für ein vollständiges Beispiel.

---

## `kamerplanter.refresh_data`

Erzwingt erneutes Polling aller 6 Coordinatoren. Nutze ihn nach manuellen Änderungen im Kamerplanter-Backend.

```yaml
service: kamerplanter.refresh_data
```

---

## `kamerplanter.clear_cache`

Leert den Coordinator-Cache. Das erzwingt einen vollständigen Neuaufbau aller Daten.

```yaml
service: kamerplanter.clear_cache
```

!!! warning "Cache leeren"
    Dieser Service löscht alle zwischengespeicherten Daten. Danach lädt er alles neu vom Backend. Verwende ihn nur bei Datenproblemen. Im Normalbetrieb reicht `refresh_data`.
