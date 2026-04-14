# Entities

Die Integration erstellt automatisch Entities fuer alle ausgewaehlten Pflanzen, Standorte und Tanks. Jede Entity gehoert zu einem der [5 Coordinators](../development/architecture.md#coordinators-coordinatorpy) und wird in dessen Polling-Intervall aktualisiert.

---

## Pflanzen-Sensoren

**Pro Pflanzen-Instanz** (Plant Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_{key}_phase` | Aktuelle Wachstumsphase | `flowering` |
| `sensor.kp_{key}_days_in_phase` | Tage in aktueller Phase | `14` |
| `sensor.kp_{key}_nutrient_plan` | Zugewiesener Naehrplan | `Bloom Week 3` |
| `sensor.kp_{key}_phase_timeline` | Phasenverlauf mit Attributen | siehe [Templates](automations.md#phasen-attribute-per-jinja2-template) |
| `sensor.kp_{key}_next_phase` | Naechste geplante Phase | `ripening` |
| `sensor.kp_{key}_vpd_target` | VPD-Sollwert fuer aktuelle Phase (kPa) | `1.2` |
| `sensor.kp_{key}_ec_target` | EC-Sollwert fuer aktuelle Phase (mS/cm) | `1.8` |
| `sensor.kp_{key}_days_until_watering` | Tage bis zur naechsten Bewasserung | `2` |
| `sensor.kp_{key}_next_watering` | Datum der naechsten Bewasserung | `2026-04-16` |
| `sensor.kp_{key}_active_channels` | Aktive Duengekanale | `2` |
| `sensor.kp_{key}_{channel}_mix` | Mischverhaeltnis pro Kanal (ml/L) | Attribute: Duengermengen |

!!! info "Phasen-Enum"
    Moegliche Werte fuer `_phase`: `germination`, `seedling`, `vegetative`, `flowering`, `ripening`, `harvest`, `dormancy`, `flushing`, `drying`, `curing`, `juvenile`, `climbing`, `mature`, `senescence`, `leaf_phase`, `short_day_induction`

---

## Run-Sensoren

**Pro Pflanzdurchlauf** (Run Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_{key}_status` | Run-Status | `active` |
| `sensor.kp_{key}_plant_count` | Anzahl Pflanzen im Run | `6` |
| `sensor.kp_{key}_nutrient_plan` | Naehrplan des Runs | `Grow Master` |
| `sensor.kp_{key}_phase_timeline` | Phasenverlauf des Runs | Attribute pro Phase |
| `sensor.kp_{key}_next_phase` | Naechste Phase | `flowering` |
| `sensor.kp_{key}_{channel}_mix` | Mischverhaeltnis pro Kanal | Attribute: Duengermengen |

!!! tip "Run-spezifische Attribute"
    Bei Runs stehen zusaetzlich `phase_week`, `phase_progress_pct` und `remaining_days` als Attribute auf dem `phase_timeline`-Sensor zur Verfuegung.

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
| `sensor.kp_loc_{key}_run_nutrient_plan` | Naehrplan des Runs | `Veg Standard` |
| `sensor.kp_loc_{key}_run_next_phase` | Naechste Phase | `flowering` |
| `sensor.kp_loc_{key}_{channel}_mix` | Mischverhaeltnis pro Kanal | Attribute: Duengermengen |

---

## Tank-Sensoren

**Pro Tank** (Location Coordinator):

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_{key}_info` | Tank-Info (Name, Typ) | `Haupttank` |
| `sensor.kp_{key}_volume` | Aktuelles Volumen (L) | `45.0` |
| `sensor.kp_{key}_fill_level` | Fuellstand in Prozent | `75` |

---

## Server-Sensoren

| Entity | Beschreibung | Beispielwert |
|--------|-------------|-------------|
| `sensor.kp_tasks_due_today` | Heute faellige Aufgaben | `3` |
| `sensor.kp_tasks_overdue` | Ueberfaellige Aufgaben | `1` |
| `sensor.kp_next_watering` | Naechster Giesstermin | `2026-04-15` |

---

## Binary Sensors

| Entity | Beschreibung | Coordinator |
|--------|-------------|-------------|
| `binary_sensor.kp_{key}_needs_attention` | Pflanze hat ueberfaellige Aufgaben | Alert |
| `binary_sensor.kp_loc_{key}_needs_attention` | Standort hat ueberfaellige Aufgaben | Alert |
| `binary_sensor.kp_sensor_offline` | Mindestens ein Sensor offline | Alert |
| `binary_sensor.kp_care_overdue` | Pflege-Aufgaben ueberfaellig | Alert |

!!! example "Einsatz in Automationen"
    ```yaml
    trigger:
      - platform: state
        entity_id: binary_sensor.kp_care_overdue
        to: "on"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Pflege ueberfaellig!"
          message: "Mindestens eine Pflege-Aufgabe ist ueberfaellig."
    ```

---

## Kalender, Todo, Button

| Entity | Beschreibung | Coordinator |
|--------|-------------|-------------|
| `calendar.kp_phases` | Wachstumsphasen als Mehrtages-Events | Plant |
| `calendar.kp_tasks` | Anstehende Aufgaben mit Faelligkeitsdatum | Task |
| `todo.kp_tasks` | Aufgabenliste — Abhaken markiert Aufgabe im Backend als erledigt | Task |
| `button.kp_refresh_all` | Manueller Refresh aller Coordinatoren | — |

!!! tip "Todo-Sync"
    Wenn du eine Aufgabe in der HA-Todo-Liste abhakst, wird sie automatisch im Kamerplanter-Backend als erledigt markiert. Das loest zusaetzlich ein `kamerplanter_task_completed`-Event aus.

---

## Events

Die Integration feuert Events, die du in Automationen als Trigger verwenden kannst:

| Event | Beschreibung |
|-------|-------------|
| `kamerplanter_phase` | Phasenwechsel einer Pflanze oder eines Runs |
| `kamerplanter_care_due` | Pflege-Erinnerung faellig |
| `kamerplanter_task_due` | Aufgabe faellig |
| `kamerplanter_task_completed` | Aufgabe via Todo abgehakt |
| `kamerplanter_tank_alert` | Tank-Alarm (niedriger Fuellstand, alte Loesung) |
| `kamerplanter_harvest` | Ernte-Benachrichtigung |
| `kamerplanter_ipm_alert` | Schaedlings-/Krankheitsalarm |
| `kamerplanter_sensor_alert` | Sensor offline oder Schwellenwert ueberschritten |
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
