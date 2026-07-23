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

### Neu

- **Frostwarnung:** Neuer Weather-Coordinator mit proaktivem Frost-Vorhersage-Sensor pro Standort (`binary_sensor.kp_site_{key}_frost_forecast`)
- **Interaktive Task-Card** mit Start-/Abschließen-/Überspringen-Aktionen
- Drei neue Services: `start_task`, `complete_task`, `skip_task`
- Sichtbarkeits-Umschalter für Card-Sektionen, neu gestaltetes Tages-Badge

### Behoben

- Care-Card zeigt jetzt Live-Aufgaben und die konkrete Pflegeaktivität statt einer statischen Vorschau
- Karten-Overflow eingedämmt und Dichte im Sections-Modus verbessert
- Geräte-Picker auf Pflanzen-/Run-Geräte beschränkt; menschenlesbare Pflanzennamen statt Code-Slugs
- Veröffentlichte Tanks erscheinen als HA-Geräte unabhängig vom Standort-Publishing
- YAML-Ressourcenmodus für Lovelace meldet sich jetzt über ein Repair-Issue statt lautlos zu scheitern

### Sonstiges

- MIT-Lizenz ergänzt

## 0.1.5

Wartungsrelease: nur Änderungen an Release-Automation und CI, keine funktionalen Änderungen an der Integration.

## 0.1.4

### Neu

- **IPM-Entities** (Integrierter Pflanzenschutz): Schädlingsdruck, Karenz und Ernte-Sicherheit als Sensoren plus Schädlings-/Ernte-Binary-Sensors
- **mDNS/Zeroconf-Auto-Discovery:** Backends, die `_kamerplanter._tcp.local.` ankündigen, werden automatisch erkannt
- Opt-in-Filter für die in Home Assistant veröffentlichten Objekte
- Kompaktes 2-Spalten-Grid-Layout für alle Cards
- `AUDIENCES.md` und Portfolio-Manifest ergänzt

## 0.1.3

Wartungsrelease: Docs-Deploy auf einen release-getriggerten Workflow umgestellt.

## 0.1.2

Wartungsrelease: CI-Workflows für Release-Automatisierung und Automerge.

## 0.1.1

Wartungsrelease: Release-Drafter-Workflow; Doku-Lücken geschlossen und auf mkdocs-material umgestellt.

## 0.1.0 (Initial Release)

### Integration

- Config Flow mit URL, API-Key, Tenant-Auswahl
- Reauth-Flow (neuer API-Key) und Reconfigure-Flow (Server-URL ändern)
- 5 Coordinators (Plant, Location, Run, Alert, Task) mit konfigurierbaren Polling-Intervallen

### Entities

- Sensoren für Pflanzen (Phase, Tage in Phase, Nährplan, Bewässerung)
- Sensoren für Runs (Status, Pflanzenanzahl, Phasenverlauf)
- Sensoren für Standorte (Typ, aktive Runs/Pflanzen, Run-Phase)
- Sensoren für Tanks (Info, Volumen)
- Server-Sensoren (fällige/überfällige Aufgaben, nächster Gießtermin)
- Binary Sensors (Attention, Care, Sensor Status)
- Calendar Entities (Phasen, Aufgaben)
- Todo Entity mit Backend-Sync

### Services

- `fill_tank` — Tank füllen mit EC (elektrische Leitfähigkeit)/pH/Notizen
- `water_channel` — Kanal gießen mit Applikationsmethode und Messwerten
- `confirm_care` — Pflege bestätigen/überspringen
- `refresh_data` — Alle Coordinators neu pollen
- `clear_cache` — Coordinator-Cache leeren

### Cards & UI

- 5 Custom Lovelace Cards (Plant, Mix, Tank, Care, Houseplant)
- 11 Event-Typen für Automationen
- DE/EN Translations
- Diagnostics
