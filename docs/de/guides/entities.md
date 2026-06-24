---
title: Entities
audience:
  - ha-end-users
  - self-hosting-admin
content_mode: reference
track: user-docs
last_updated: 2026-06-24
---
# Entities

Die Integration legt Entities für dich an. Du bekommst je einen Satz pro gewählter Pflanze, pro Standort und pro Tank. Jede Entity gehört zu einem der [6 Coordinators](../development/architecture.md#coordinators-coordinatorpy). Sie wird in dessen Polling-Intervall aktualisiert.

---

## Pflanzen-Sensoren

**Pro Pflanzen-Instanz** (Plant Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_{key}_phase` | Aktuelle Wachstumsphase | `flowering` |
| `sensor.kp_{key}_days_in_phase` | Tage in aktueller Phase | `14` |
| `sensor.kp_{key}_nutrient_plan` | Zugewiesener Nährplan | `Bloom Week 3` |
| `sensor.kp_{key}_phase_timeline` | Phasenverlauf mit Attributen | siehe [Templates](automations.md#phasen-attribute-per-jinja2-template) |
| `sensor.kp_{key}_next_phase` | Nächste geplante Phase | `ripening` |
| `sensor.kp_{key}_days_until_watering` | Tage bis zur nächsten Bewässerung | `2` |
| `sensor.kp_{key}_next_watering` | Datum der nächsten Bewässerung | `2026-04-16` |
| `sensor.kp_{key}_active_channels` | Aktive Düngekanäle | `2` |
| `sensor.kp_{key}_{channel}_mix` | Mischverhältnis pro Kanal (ml/L) | Attribute: Düngermengen |

!!! info "Phasen-Enum"
    Mögliche Werte für `_phase`:

    - `germination`
    - `seedling`
    - `vegetative`
    - `flowering`
    - `ripening`
    - `harvest`
    - `dormancy`
    - `flushing`
    - `drying`
    - `curing`
    - `juvenile`
    - `climbing`
    - `mature`
    - `senescence`
    - `leaf_phase`
    - `short_day_induction`

---

## Run-Sensoren

**Pro Pflanzdurchlauf** (Run Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_{key}_status` | Run-Status | `active` |
| `sensor.kp_{key}_plant_count` | Anzahl Pflanzen im Run | `6` |
| `sensor.kp_{key}_nutrient_plan` | Nährplan des Runs | `Grow Master` |
| `sensor.kp_{key}_phase_timeline` | Phasenverlauf des Runs | Attribute pro Phase |
| `sensor.kp_{key}_next_phase` | Nächste Phase | `flowering` |
| `sensor.kp_{key}_{channel}_mix` | Mischverhältnis pro Kanal | Attribute: Düngermengen |

!!! tip "Run-spezifische Attribute"
    Runs bieten zusätzliche Attribute auf dem `phase_timeline`-Sensor:

    - `phase_week`
    - `phase_progress_pct`
    - `remaining_days`

---

## Standort-Sensoren

**Pro Standort** (Location Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_loc_{key}_type` | Standorttyp | `tent` |
| `sensor.kp_loc_{key}_active_run_count` | Anzahl aktiver Runs | `1` |
| `sensor.kp_loc_{key}_active_plant_count` | Anzahl aktiver Pflanzen | `4` |
| `sensor.kp_loc_{key}_plant_count` | Gesamtanzahl Pflanzen | `6` |
| `sensor.kp_loc_{key}_run_status` | Status des aktiven Runs | `active` |
| `sensor.kp_loc_{key}_run_phase` | Phase des aktiven Runs | `vegetative` |
| `sensor.kp_loc_{key}_run_days_in_phase` | Tage in aktueller Phase | `21` |
| `sensor.kp_loc_{key}_run_nutrient_plan` | Nährplan des Runs | `Veg Standard` |
| `sensor.kp_loc_{key}_run_next_phase` | Nächste Phase | `flowering` |
| `sensor.kp_loc_{key}_{channel}_mix` | Mischverhältnis pro Kanal | Attribute: Düngermengen |

---

## Tank-Sensoren

**Pro Tank** (Location Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_{key}_info` | Tank-Info (Name, Typ) | `Haupttank` |
| `sensor.kp_{key}_volume` | Aktuelles Volumen (L) | `45.0` |

---

## IPM-Sensoren (Integrierter Pflanzenschutz)

**Pro Pflanze** (IPM Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_{key}_pest_pressure` | Schädlingsdruck (Enum: `none`, `low`, `medium`, `high`, `critical`) | `low` |
| `sensor.kp_{key}_karenz_remaining` | Verbleibende Karenz bis zur Ernte (Tage) | `3` |
| `sensor.kp_{key}_last_inspection_days` | Tage seit der letzten Kontrolle | `5` |

---

## Server-Sensoren

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_tasks_due_today` | Heute fällige Aufgaben | `3` |
| `sensor.kp_tasks_overdue` | Überfällige Aufgaben | `1` |
| `sensor.kp_next_watering` | Nächster Gießtermin | `2026-04-15` |

---

## Binary Sensors

| Entity | Beschreibung | Coordinator |
|--------|-------------|-------------|
| `binary_sensor.kp_{key}_needs_attention` | Pflanze hat überfällige Aufgaben | Alert |
| `binary_sensor.kp_loc_{key}_needs_attention` | Standort hat überfällige Aufgaben | Alert |
| `binary_sensor.kp_sensor_offline` | Mindestens ein Sensor offline | Alert |
| `binary_sensor.kp_care_overdue` | Pflege-Aufgaben überfällig | Alert |
| `binary_sensor.kp_{key}_harvest_safe` | Ernte unbedenklich (Karenzzeit abgelaufen) | IPM |
| `binary_sensor.kp_{key}_pest_alert` | Schädlingsbefall erkannt | IPM |

!!! example "Einsatz in Automationen"
    ```yaml
    trigger:
      - platform: state
        entity_id: binary_sensor.kp_care_overdue
        to: "on"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Pflege überfällig!"
          message: "Mindestens eine Pflege-Aufgabe ist überfällig."
    ```

---

## Kalender, Todo, Button

| Entity | Beschreibung | Coordinator |
|--------|-------------|-------------|
| `calendar.kp_phases` | Wachstumsphasen als Mehrtages-Events | Plant |
| `calendar.kp_tasks` | Anstehende Aufgaben mit Fälligkeitsdatum | Task |
| `todo.kp_tasks` | Aufgabenliste — Abhaken markiert Aufgabe im Backend als erledigt | Task |
| `button.kp_refresh_all` | Manueller Refresh aller Coordinatoren | — |

!!! tip "Todo-Sync"
    Wenn du eine Aufgabe in der HA-Todo-Liste abhakst, wird sie automatisch im Kamerplanter-Backend als erledigt markiert. Das löst zusätzlich ein `kamerplanter_task_completed`-Event aus.

---

## Events

Die Integration sendet Events, die du in Automationen als Trigger verwenden kannst:

| Event | Beschreibung |
|-------|-------------|
| `kamerplanter_phase` | Phasenwechsel einer Pflanze oder eines Runs |
| `kamerplanter_care_due` | Pflege-Erinnerung fällig |
| `kamerplanter_task_due` | Aufgabe fällig |
| `kamerplanter_task_completed` | Aufgabe via Todo abgehakt |
| `kamerplanter_tank_alert` | Tank-Alarm (niedriger Füllstand, alte Lösung) |
| `kamerplanter_harvest` | Ernte-Benachrichtigung |
| `kamerplanter_ipm_alert` | Schädlings-/Krankheitsalarm (IPM — Integrated Pest Management, integrierter Pflanzenschutz) |
| `kamerplanter_sensor_alert` | Sensor offline oder Schwellenwert überschritten |
| `kamerplanter_weather_alert` | Wetterwarnung |
| `kamerplanter_seasonal` | Saisonale Erinnerung |
| `kamerplanter_data_refreshed` | Manueller Refresh via Button |

!!! example "Event als Trigger"
    ```yaml
    trigger:
      - platform: event
        event_type: kamerplanter_phase
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.new_phase == 'flowering' }}"
    ```
