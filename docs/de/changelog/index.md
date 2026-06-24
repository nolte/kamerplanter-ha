---
title: Changelog
audience:
  - ha-end-users
  - self-hosting-admin
  - maintainers
content_mode: meta
track: user-docs
last_updated: 2026-06-24
---
# Changelog

## 0.1.0 (Initial Release)

### Integration

- Config Flow mit URL, API-Key, Tenant-Auswahl
- Reauth-Flow (neuer API-Key) und Reconfigure-Flow (Server-URL ändern)
- 5 Coordinators (Plant, Location, Run, Alert, Task) mit konfigurierbaren Polling-Intervallen

### Entities

- Sensoren für Pflanzen (Phase, Tage in Phase, Nährplan, Bewässerung)
- Sensoren für Runs (Status, Pflanzenanzahl, Phasenverlauf)
- Sensoren für Standorte (Typ, aktive Runs/Pflanzen, Run-Phase)
- Sensoren für Tanks (Info, Volumen, Füllstand)
- Server-Sensoren (fällige/überfällige Aufgaben, nächster Gießtermin)
- Binary Sensors (Attention, Care, Sensor Status)
- Calendar Entities (Phasen, Aufgaben)
- Todo Entity mit Backend-Sync

### Services

- `fill_tank` — Tank füllen mit EC/pH/Notizen
- `water_channel` — Kanal gießen mit Applikationsmethode und Messwerten
- `confirm_care` — Pflege bestätigen/überspringen
- `refresh_data` — Alle Coordinatoren neu pollen
- `clear_cache` — Coordinator-Cache leeren

### Cards & UI

- 5 Custom Lovelace Cards (Plant, Mix, Tank, Care, Houseplant)
- 11 Event-Typen für Automationen
- DE/EN Translations
- Diagnostics
