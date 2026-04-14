# Changelog

## 0.1.0 (Initial Release)

### Integration

- Config Flow mit URL, API-Key, Tenant-Auswahl
- Reauth-Flow (neuer API-Key) und Reconfigure-Flow (Server-URL aendern)
- 5 Coordinators (Plant, Location, Run, Alert, Task) mit konfigurierbaren Polling-Intervallen

### Entities

- Sensoren fuer Pflanzen (Phase, Tage in Phase, VPD/EC-Sollwerte, Naehrplan, Bewaesserung)
- Sensoren fuer Runs (Status, Pflanzenanzahl, Phasenverlauf)
- Sensoren fuer Standorte (Typ, aktive Runs/Pflanzen, Run-Phase)
- Sensoren fuer Tanks (Info, Volumen, Fuellstand)
- Server-Sensoren (faellige/ueberfaellige Aufgaben, naechster Giesstermin)
- Binary Sensors (Attention, Care, Sensor Status)
- Calendar Entities (Phasen, Aufgaben)
- Todo Entity mit Backend-Sync

### Services

- `fill_tank` — Tank fuellen mit EC/pH/Notizen
- `water_channel` — Kanal giessen mit Applikationsmethode und Messwerten
- `confirm_care` — Pflege bestaetigen/ueberspringen
- `refresh_data` — Alle Coordinatoren neu pollen
- `clear_cache` — Coordinator-Cache leeren

### Cards & UI

- 5 Custom Lovelace Cards (Plant, Mix, Tank, Care, Houseplant)
- 11 Event-Typen fuer Automationen
- DE/EN Translations
- Diagnostics
