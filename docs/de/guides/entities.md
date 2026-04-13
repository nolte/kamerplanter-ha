# Entities

Die Integration erstellt automatisch Entities fuer alle ausgewaehlten Pflanzen, Standorte und Tanks.

## Pflanzen-Sensoren

**Pro Pflanzen-Instanz:**

| Entity | Beschreibung |
|--------|-------------|
| `sensor.kp_{key}_phase` | Aktuelle Wachstumsphase |
| `sensor.kp_{key}_days_in_phase` | Tage in aktueller Phase |
| `sensor.kp_{key}_nutrient_plan` | Zugewiesener Naehrplan |
| `sensor.kp_{key}_phase_timeline` | Phasenverlauf mit Attributen |
| `sensor.kp_{key}_next_phase` | Naechste geplante Phase |
| `sensor.kp_{key}_active_channels` | Aktive Duengekanale |
| `sensor.kp_{key}_{channel}_mix` | Mischverhaeltnis pro Kanal (ml/L) |

**Pro Pflanzdurchlauf (Run):**

| Entity | Beschreibung |
|--------|-------------|
| `sensor.kp_{key}_status` | Run-Status |
| `sensor.kp_{key}_plant_count` | Anzahl Pflanzen im Run |
| `sensor.kp_{key}_nutrient_plan` | Naehrplan des Runs |
| `sensor.kp_{key}_phase_timeline` | Phasenverlauf des Runs |
| `sensor.kp_{key}_next_phase` | Naechste Phase |
| `sensor.kp_{key}_{channel}_mix` | Mischverhaeltnis pro Kanal |

## Standort-Sensoren

**Pro Standort:**

| Entity | Beschreibung |
|--------|-------------|
| `sensor.kp_loc_{key}_type` | Standorttyp |
| `sensor.kp_loc_{key}_active_run_count` | Anzahl aktiver Runs |
| `sensor.kp_loc_{key}_active_plant_count` | Anzahl aktiver Pflanzen |
| `sensor.kp_loc_{key}_run_phase` | Phase des aktiven Runs |
| `sensor.kp_loc_{key}_run_days_in_phase` | Tage in aktueller Phase |
| `sensor.kp_loc_{key}_run_nutrient_plan` | Naehrplan des Runs |
| `sensor.kp_loc_{key}_run_next_phase` | Naechste Phase |
| `sensor.kp_loc_{key}_{channel}_mix` | Mischverhaeltnis pro Kanal |

## Tank-Sensoren

**Pro Tank:**

| Entity | Beschreibung |
|--------|-------------|
| `sensor.kp_{key}_info` | Tank-Info (Name, Typ) |
| `sensor.kp_{key}_volume` | Aktuelles Volumen |

## Server-Sensoren

| Entity | Beschreibung |
|--------|-------------|
| `sensor.kp_tasks_due_today` | Heute faellige Aufgaben |
| `sensor.kp_tasks_overdue` | Ueberfaellige Aufgaben |
| `sensor.kp_next_watering` | Naechster Giesstermin |

## Binary Sensors

| Entity | Beschreibung |
|--------|-------------|
| `binary_sensor.kp_{key}_needs_attention` | Pflanze hat ueberfaellige Aufgaben |
| `binary_sensor.kp_loc_{key}_needs_attention` | Standort hat ueberfaellige Aufgaben |
| `binary_sensor.kp_sensor_offline` | Mindestens ein Sensor offline |
| `binary_sensor.kp_care_overdue` | Pflege-Aufgaben ueberfaellig |

## Kalender, Todo, Button

| Entity | Beschreibung |
|--------|-------------|
| `calendar.kp_phases` | Wachstumsphasen als Mehrtages-Events |
| `calendar.kp_tasks` | Anstehende Aufgaben mit Faelligkeitsdatum |
| `todo.kp_tasks` | Aufgabenliste — Abhaken markiert Aufgabe im Backend als erledigt |
| `button.kp_refresh_all` | Manueller Refresh aller Coordinatoren |

## Events

| Event | Beschreibung |
|-------|-------------|
| `kamerplanter_task_completed` | Aufgabe via Todo abgehakt |
| `kamerplanter_data_refreshed` | Manueller Refresh via Button |
| `kamerplanter_care_due` | Pflege-Erinnerung faellig |
| `kamerplanter_phase` | Phasenwechsel |
| `kamerplanter_tank_alert` | Tank-Alarm (niedriger Fuellstand, alte Loesung) |
| `kamerplanter_harvest` | Ernte-Benachrichtigung |
| `kamerplanter_ipm_alert` | Schaedlings-/Krankheitsalarm |
| `kamerplanter_sensor_alert` | Sensor offline/Schwellenwert |
| `kamerplanter_task_due` | Aufgabe faellig |
| `kamerplanter_weather_alert` | Wetterwarnung |
| `kamerplanter_seasonal` | Saisonale Erinnerung |
