# HA-Integrationsreview: Core REQs (003, 005, 014, 018)

> Erstellt: 2026-02-28
> Referenz: HA-CUSTOM-INTEGRATION.md v1.1
> Methodik: Drei-Seiten-Modell (A = KP->HA Export, B = HA->KP Import, C = KP->HA Aktorik)
> Basis-Review: smart-home-ha-integration-review.md v2.0

## Zusammenfassung

Die vier Core-REQs (003, 005, 014, 018) bilden zusammen den **Sensor-Aktor-Regelkreis** und sind damit die HA-relevantesten Anforderungen des gesamten Systems. Die Gesamtbewertung nach Seiten:

| Seite | Bewertung | Kommentar |
|-------|-----------|-----------|
| **A (KP->HA Export)** | 3/5 | Entity-Mapping in HA-CUSTOM-INTEGRATION.md gut definiert. Aber: REQ-003 hat keine dedizierten API-Endpoints fuer HA-relevante Daten (Phasen-History, VPD-Targets). REQ-014 hat Alerts nur als berechnete Logik, kein eigenstaendiger `/alerts`-Endpoint. Phasen-Transitions fehlen als Push-Event. |
| **B (HA->KP Import)** | 5/5 | REQ-005 ist das Paradebeispiel fuer HA-Integration. `ha_entity_id` auf Sensor-Node, `source`-Tracking, Fallback-Kette, `HomeAssistantConnector` mit REST+History-API. REQ-014 `TankState.source: 'home_assistant'` korrekt modelliert. |
| **C (KP->HA Aktorik)** | 4/5 | REQ-018 deckt Aktorik umfassend ab: `ha_entity_id`, Service-Calls, Fail-Safe, Hysterese, VPD-Controller. Luecke: `PhaseTransitionHandler.on_phase_transition()` erzeugt Steuerungsanweisungen, aber der Mechanismus wie diese an HA-Aktoren delegiert werden (Celery-Task? Synchron?) ist nicht spezifiziert. Modus B (Sollwert-Export) hat keinen definierten Feedback-Pfad. |
| **Optionalitaet** | 5/5 | Alle vier REQs funktionieren vollstaendig ohne HA. Manuelle Eingabe/Tasks als durchgaengiger Fallback. |

**Hauptergebnis:** Die groessten Luecken liegen nicht in den REQ-Dokumenten selbst, sondern in der **Schnittstelle zwischen REQ und HA-CUSTOM-INTEGRATION.md**. Die Custom Integration referenziert API-Endpoints und Entities, die in den REQs nicht explizit als HA-Exportschnittstelle definiert sind. Es fehlen:

1. Dedizierte Bulk-/Summary-Endpoints fuer Coordinator-Polling
2. MQTT-Event-Topics fuer zeitkritische Zustandsaenderungen
3. Webhook-Endpoint fuer Modus-B-Feedback (HA->KP Aktionsbestaetigung)
4. Hysterese-Parameter als exportierte Entities (Modus B)

---

## REQ-003: Phasensteuerung

### Status: Maessig vorbereitet (2/5)

REQ-003 definiert die State-Machine fuer Pflanzenphasen, VPD-Targets, Photoperioden und NPK-Profile — alles Kernwerte fuer HA-Automationen. Aber: Das REQ fokussiert auf interne Domaenenlogik (PhaseTransitionEngine, VPD-Berechnung) und definiert **keine eigene REST-API-Sektion**. Die API-Endpoints existieren nur implizit ueber die implementierten Backend-Router.

### Seite A (Export)

**In HA-CUSTOM-INTEGRATION.md spezifizierte Entities:**

| Entity | Quelle | Coordinator | Problem |
|--------|--------|-------------|---------|
| `sensor.kp_{plant}_phase` | `current_phase` | PlantCoordinator (300s) | OK — `current_phase` ist Edge auf PlantInstance |
| `sensor.kp_{plant}_days_in_phase` | `phase_histories.entered_at` (berechnet) | PlantCoordinator (300s) | Berechnung muss im Coordinator erfolgen, nicht von API geliefert |
| `sensor.kp_{plant}_vpd_target` | `requirement_profiles.vpd_target_kpa` | PlantCoordinator (300s) | Kein einzelner Endpoint; muss aus Phase -> RequirementProfile -> vpd_target_kpa aufgeloest werden |
| `sensor.kp_{plant}_ec_target` | `nutrient_profiles.target_ec_ms` | PlantCoordinator (300s) | Wie vpd_target: Graph-Traversierung noetig |
| `sensor.kp_{plant}_photoperiod` | `requirement_profiles.photoperiod_hours` | PlantCoordinator (300s) | Wie vpd_target |
| `sensor.kp_{plant}_gdd_accumulated` | GDD-Tracking (berechnet) | PlantCoordinator (300s) | GDD-Akkumulation existiert als Engine-Logik, aber kein dedizierter API-Wert |

**Fehlende Entities:**

| Entity-Vorschlag | Quelle | Begruendung |
|------------------|--------|-------------|
| `sensor.kp_{plant}_phase_progress_pct` | `days_in_phase / typical_duration_days * 100` | Prozentuale Fortschrittsanzeige fuer HA-Dashboard. `typical_duration_days` auf GrowthPhase vorhanden. |
| `sensor.kp_{plant}_next_phase` | `sequence_order + 1` aus PhaseDefinition | Fuer Automationen: "Wenn naechste Phase = flowering, bereite Licht-Umstellung vor" |
| `sensor.kp_{plant}_transition_type` | `time_based` oder `manual` | Ob Uebergang automatisch kommt oder manuellen Trigger braucht |
| `sensor.kp_{location}_dominant_phase` | Meistvertretene Phase der aktiven Pflanzen | Fuer Location-Level-Automationen (alle Pflanzen in Bluete -> Lichtprogramm) |
| `binary_sensor.kp_{plant}_phase_overdue` | `days_in_phase > typical_duration_days * 1.2` | Alert wenn Phase unerwartet lang dauert |

### Seite B (Import)

REQ-003 ist **kein Sensor-Consumer**. Es empfaengt keine Daten von HA. Die Phasen-State-Machine wird durch REQ-005-Sensordaten (VPD-Berechnung) und REQ-018 (Aktor-Anpassung) indirekt beeinflusst, aber der Datenfluss ist:
- REQ-005 (Sensoren) -> REQ-003 (berechnet VPD aus Temp+Humidity) -> REQ-018 (setzt Aktoren)

**Kein HA-Import-Bedarf fuer REQ-003 selbst.** Der VPD-Calculator in REQ-003 nutzt Sensor-Observations aus REQ-005, die bereits ueber `ha_entity_id` korrekt gemappt sind.

### Seite C (Steuerung)

REQ-003 ist der **Trigger-Lieferant** fuer REQ-018-Steuerung:

- Phasenwechsel -> `PhaseTransitionHandler.on_phase_transition()` -> Aktor-Befehle
- REQ-018 `phase_profile` Edge: `growth_phases -> phase_control_profiles`
- `PhaseControlProfile` definiert Sollwerte (Photoperiode, VPD, Temperatur, CO2)

**Luecke:** REQ-003 definiert den Phasenwechsel als `PhaseTransitionEngine.transition_to_phase()`, aber der **Callback-Mechanismus zu REQ-018** ist nicht spezifiziert:
- Wer ruft `PhaseTransitionHandler.on_phase_transition()` auf?
- Ist das ein Celery-Signal? Ein synchroner Call? Ein Event-Bus?
- REQ-018 listet den Celery-Task `calculate_gradual_transitions` (stuendlich), aber der initiale Trigger fehlt.

**Steuerungsmodus-Grenzziehung:**

| Modus A (KP steuert direkt) | Modus B (KP liefert Sollwerte) |
|------------------------------|-------------------------------|
| KP ruft `HomeAssistantClient.call_service()` bei Phasenwechsel | KP aktualisiert `sensor.kp_{plant}_photoperiod` etc. |
| KP aktiviert/deaktiviert ControlSchedules | HA-Automation triggert auf Entity-State-Change |
| Graduelle Transition (7 Tage) wird von KP berechnet | HA muesste den graduellen Uebergang selbst berechnen (nicht praktikabel) |

**Problem bei Modus B:** Graduelle Phasenwechsel-Transitionen (z.B. 18h -> 12h ueber 7 Tage) erfordern, dass KP die Zwischenwerte taggenau als Sensor-Entities publiziert. HA-CUSTOM-INTEGRATION.md definiert nur `sensor.kp_{plant}_photoperiod` als statischen Wert. Fuer Modus B muesste es ein `sensor.kp_{plant}_photoperiod_current` (interpolierter Tageswert waehrend Transition) und `sensor.kp_{plant}_photoperiod_target` (Endwert) geben.

### Fehlende API-Endpoints

| Endpoint | Zweck | Consumer |
|----------|-------|----------|
| `GET /api/v1/t/{slug}/plants/{key}/phase-summary` | Zusammengefasst: current_phase, days_in_phase, vpd_target, ec_target, photoperiod, gdd, phase_progress_pct, next_phase | PlantCoordinator |
| `GET /api/v1/t/{slug}/plants/phase-summaries` | Bulk-Version fuer alle aktiven Pflanzen eines Tenants | PlantCoordinator (effizienter als N+1 Requests) |
| `GET /api/v1/t/{slug}/locations/{key}/dominant-phase` | Dominante Phase aller aktiven Pflanzen einer Location | LocationCoordinator |

### MQTT-Events noetig

| Topic | Payload | Begruendung |
|-------|---------|-------------|
| `kamerplanter/{tenant}/events/phase-transition` | `{plant_key, old_phase, new_phase, timestamp, transition_days}` | Phasenwechsel ist zeitkritisch fuer Lichtprogramm-Umstellung. 300s Polling kann bis zu 5 Minuten Verzoegerung bedeuten — akzeptabel, aber Push waere besser. |
| `kamerplanter/{tenant}/events/phase-overdue` | `{plant_key, phase, days_in_phase, expected_days}` | Phase dauert laenger als erwartet — Anomalie-Detection |

### Blueprint-Vorschlaege

**Blueprint 6: Phasenwechsel -> Graduelle Lichtanpassung (Modus B)**

```yaml
# Problem: Modus B kann graduelle Transition nicht nativ
# Loesung: HA Automation mit linearer Interpolation
alias: "KP: Graduelle Photoperiode-Anpassung"
trigger:
  - platform: state
    entity_id: sensor.kp_northern_lights_photoperiod
    # Trigger wenn KP den Zielwert aendert (z.B. 18 -> 12)
condition: []
action:
  # Berechne taegliche Aenderung ueber transition_days (Attribut)
  - service: input_number.set_value
    target:
      entity_id: input_number.kp_photoperiod_transition_target
    data:
      value: "{{ states('sensor.kp_northern_lights_photoperiod') }}"
  # HA-Automation kuerzt taeglich die Beleuchtungszeit
```

**Hinweis:** Dieser Blueprint ist deutlich komplexer als Modus A. Empfehlung: Graduelle Transitionen nur in Modus A (KP steuert), Modus B erhaelt sofortige Endwerte.

**Blueprint 7: Location-Phasen-Check -> Alarmierung**

```yaml
# Warnung wenn Pflanzen in unterschiedlichen Phasen an gleicher Location
alias: "KP: Gemischte Phasen Warnung"
trigger:
  - platform: template
    value_template: >
      {{ states('sensor.kp_northern_lights_phase') !=
         states('sensor.kp_white_widow_phase') }}
condition:
  - condition: template
    value_template: >
      {{ state_attr('sensor.kp_northern_lights_phase', 'location_key') ==
         state_attr('sensor.kp_white_widow_phase', 'location_key') }}
action:
  - service: notify.mobile_app_phone
    data:
      title: "Gemischte Phasen Warnung"
      message: "Pflanzen an gleicher Location sind in unterschiedlichen Phasen!"
```

---

## REQ-005: Hybrid-Sensorik

### Status: Exzellent (5/5)

REQ-005 ist das **Paradebeispiel** fuer HA-Integration im Kamerplanter-Projekt. Es definiert:
- `ha_entity_id` auf jedem Sensor-Node
- `mqtt_topic` als Alternative
- `source`-Tracking auf jeder Observation (`ha_auto`, `mqtt_auto`, `manual`, `weather_api`, etc.)
- Vollstaendige Fallback-Kette (HA -> MQTT -> Wetter-API -> manuell)
- `HomeAssistantConnector` mit REST+History-API
- Quality-Scoring differenziert nach Datenquelle
- Anomalie-Detection mit plausibler Aenderungsrate

### Seite A (Export)

**In HA-CUSTOM-INTEGRATION.md spezifizierte Entities:**

| Entity | Quelle | Status |
|--------|--------|--------|
| `sensor.kp_{location}_vpd_current` | Berechneter VPD aus Sensor-Observations | OK — berechnet im Coordinator |
| `binary_sensor.kp_sensor_offline` | SensorHealth-Pruefung | OK — aus AlertCoordinator |

**Fehlende Entities:**

| Entity-Vorschlag | Quelle | Begruendung |
|------------------|--------|-------------|
| `sensor.kp_{sensor}_quality_score` | `Observation.quality_score` (letzte) | Fuer HA-Dashboard: "Wie vertrauenswuerdig ist der Wert?" Besonders relevant bei `weather_api` (0.7) vs. `ha_auto` (1.0) |
| `sensor.kp_{location}_sensor_count` | Anzahl aktiver Sensoren | Monitoring: Wie viele Sensoren liefern Daten? |
| `binary_sensor.kp_{location}_fallback_active` | `true` wenn `source` der letzten Observation != `ha_auto` | Alert: System nutzt Fallback-Daten statt HA-Live-Daten |
| `sensor.kp_{location}_data_age_seconds` | `now() - latest_observation.timestamp` | Fuer HA: "Wie alt sind die neuesten Daten?" Trigger fuer Anomalie-Detection |

### Seite B (Import)

REQ-005 ist der **Kern der Seite B**. Vollstaendig spezifiziert:

| Aspekt | Status | Detail |
|--------|--------|--------|
| `ha_entity_id`-Mapping | Vorhanden | Auf Sensor-Node, z.B. `sensor.growzelt_temp` |
| `mqtt_topic`-Mapping | Vorhanden | Auf Sensor-Node, z.B. `kamerplanter/sensors/temp1` |
| `HomeAssistantConnector` | Vorhanden | REST-Client mit `get_sensor_state()`, `get_sensor_history()`, `test_connection()` |
| `source`-Tracking | Vorhanden | 7 Quellen: `ha_auto`, `mqtt_auto`, `modbus_auto`, `manual`, `interpolated`, `fallback`, `weather_api` |
| Fallback-Kette | Vorhanden | 4 Stufen: HA -> MQTT -> Wetter-API -> manuell |
| Quality-Scoring | Vorhanden | Differenziert: `ha_auto`=1.0, `mqtt_auto`=0.95, `manual`=0.85, `weather_api`=0.7, `interpolated`=0.6 |
| Anomalie-Detection | Vorhanden | Aenderungsraten-Pruefung, statistische Ausreisser-Erkennung |
| Graceful Degradation | Vorhanden | >6h ohne Daten -> Task-Generierung, <2h -> Interpolation |

**Verbleibende Luecken (aus Review uebernommen):**

| # | Luecke | Prioritaet | Detail |
|---|--------|------------|--------|
| B-006 | Einheiten-Konvertierung (F->C, PSI->kPa) | Niedrig | `_infer_parameter_from_entity()` erkennt Unit, aber keine Konvertierungslogik |
| B-008 | Sensor-Mapping-UI (HA-Entity-Browser) | Mittel | `ha_entity_id` ist Freitext statt Dropdown mit HA-Entity-Auswahl |
| B-009 | Multi-HA-Instanz-Support | Niedrig | Nur eine `ha_url` + `ha_token` konfigurierbar |
| B-011 | WebSocket-Subscription | Mittel | `HomeAssistantConnector` nur REST, kein HA WebSocket API (`/api/websocket`) |

### Seite C (Steuerung)

REQ-005 ist kein Aktor-Consumer — es liefert **Sensordaten als Input** fuer REQ-018 Steuerungsregeln. Der Datenfluss ist korrekt modelliert:
- `monitors` Edge: `control_rules -> sensors` (REQ-018 ueberwacht REQ-005 Sensoren)
- `sensor_parameter` in ControlRule referenziert Observation-Parameter

**Keine Luecken auf Seite C.**

### Fehlende API-Endpoints

| Endpoint | Zweck | Consumer |
|----------|-------|----------|
| `GET /api/v1/t/{slug}/sensors/health-summary` | Aggregierter Gesundheitsstatus aller Sensoren (online/offline/degraded, letzte Observation, quality_score) | AlertCoordinator |
| `GET /api/v1/t/{slug}/locations/{key}/sensor-readings/latest` | Alle aktuellen Sensorwerte einer Location in einem Call | Allgemeiner HA-Dashboard-Consumer; reduziert N+1-Abfragen |

### MQTT-Events noetig

| Topic | Payload | Begruendung |
|-------|---------|-------------|
| `kamerplanter/{tenant}/events/sensor-offline` | `{sensor_key, location_key, last_seen, parameter}` | Sensor-Ausfall ist zeitkritisch. 60s-Polling (AlertCoordinator) ist akzeptabel, aber Push waere ideal. |
| `kamerplanter/{tenant}/events/sensor-anomaly` | `{sensor_key, parameter, value, expected_range, anomaly_type}` | Unplausible Werte sofort melden (z.B. Temperatur springt um 20C in 1 Minute) |

### Blueprint-Vorschlaege

**Blueprint 8: Sensor-Fallback -> Manuelle Messung anfordern**

```yaml
alias: "KP: Sensor-Fallback aktiv -> Erinnerung"
description: "Push-Benachrichtigung wenn KP auf Fallback-Daten zurueckfaellt"
trigger:
  - platform: state
    entity_id: binary_sensor.kp_growzelt1_fallback_active
    to: "on"
    for:
      minutes: 30
condition: []
action:
  - service: notify.mobile_app_phone
    data:
      title: "Sensor-Fallback aktiv"
      message: >
        Growzelt 1 nutzt seit 30 Minuten Fallback-Daten.
        Bitte Sensoren pruefen oder manuelle Messung durchfuehren.
mode: single
```

---

## REQ-014: Tankmanagement

### Status: Gut vorbereitet (4/5)

REQ-014 hat ein klares Modell fuer Tank-Zustands-Tracking mit `source: 'home_assistant'` auf `TankState`. Die Alert-Logik (`check_alerts()`) ist umfassend — pH, EC, Temperatur, DO, ORP, Fuellstand, Algenrisiko. Die Entity-Mapping-Tabelle in HA-CUSTOM-INTEGRATION.md ist vollstaendig.

### Seite A (Export)

**In HA-CUSTOM-INTEGRATION.md spezifizierte Entities:**

| Entity | Quelle | Coordinator | Status |
|--------|--------|-------------|--------|
| `sensor.kp_{tank}_ec` | `TankState.ec_ms` | TankCoordinator (120s) | OK |
| `sensor.kp_{tank}_ph` | `TankState.ph` | TankCoordinator (120s) | OK |
| `sensor.kp_{tank}_fill_level` | `TankState.fill_level_percent` | TankCoordinator (120s) | OK |
| `sensor.kp_{tank}_water_temp` | `TankState.water_temp_celsius` | TankCoordinator (120s) | OK |

**API-Endpoint fuer TankCoordinator:**
- `GET /api/v1/tanks/` — Alle Tanks
- `GET /api/v1/tanks/{id}/states/latest` — Aktuellster Zustand

**Problem:** TankCoordinator muss fuer jeden Tank separat `GET /tanks/{id}/states/latest` aufrufen. Bei 5 Tanks = 6 API-Calls pro Polling-Zyklus (1 List + 5 State).

**Fehlende Entities:**

| Entity-Vorschlag | Quelle | Begruendung |
|------------------|--------|-------------|
| `sensor.kp_{tank}_dissolved_oxygen` | `TankState.dissolved_oxygen_mgl` | Kritisch fuer Hydroponik (>6 mg/L optimal, <4 mg/L kritisch). Im TankState-Modell vorhanden, aber nicht in HA-CUSTOM-INTEGRATION.md Entity-Tabelle. |
| `sensor.kp_{tank}_orp` | `TankState.orp_mv` | Relevant fuer Rezirkulation mit UV/Ozon-Sterilisation. Im TankState-Modell vorhanden, nicht exportiert. |
| `sensor.kp_{tank}_solution_age_days` | Berechnet aus letztem `full_change` TankFillEvent | Loesungsalter ist ein zentraler Alert-Trigger (temperaturkorrigierte Q10-Regel). Als HA-Sensor nuetzlich fuer Dashboard. |
| `binary_sensor.kp_{tank}_alert_active` | `check_alerts()` Result | Aggregierter Alert-Status pro Tank. `binary_sensor.kp_{plant}_needs_attention` existiert, aber kein Tank-Aequivalent. |
| `sensor.kp_{tank}_ec_deviation_pct` | `abs(current_ec - target_ec) / target_ec * 100` | EC-Abweichung vom Plan-Ziel als Prozentwert fuer HA-Automationen |
| `sensor.kp_{tank}_algae_risk` | `algae_risk_score` (0-5) | Algenrisiko-Score fuer Dashboard und Automationen (z.B. UV-Sterilisator einschalten) |
| `sensor.kp_{tank}_next_water_change` | `last_full_change + interval_days` aus MaintenanceSchedule | Countdown bis zum naechsten Wasserwechsel |

### Seite B (Import)

`TankState.source: Literal['manual', 'sensor', 'home_assistant']` ist korrekt modelliert. Der Import-Pfad:

1. HA-Sensor (z.B. ESPHome pH-Sonde) liefert Wert an HA
2. KP `HomeAssistantConnector.get_sensor_state(ha_entity_id)` pollt HA
3. KP erstellt `TankState` mit `source='home_assistant'`

**Luecke:** Das Mapping `Tank -> Sensor -> ha_entity_id` ist **nicht explizit definiert**. REQ-014 definiert kein `ha_entity_id`-Feld auf dem Tank oder TankState. Die Verknuepfung laeuft indirekt ueber:
- Tank `has_tank` -> Location `located_at` -> Sensor (REQ-005) mit `ha_entity_id`
- Oder: `parameter: 'ec'` und Location-Zuordnung

**Empfehlung:** Explizites Mapping auf Tank-Ebene hinzufuegen:

```python
class TankDefinition(BaseModel):
    # ... existierende Felder ...
    ha_ec_entity_id: Optional[str] = None      # z.B. "sensor.tank1_ec"
    ha_ph_entity_id: Optional[str] = None      # z.B. "sensor.tank1_ph"
    ha_fill_entity_id: Optional[str] = None    # z.B. "sensor.tank1_level"
    ha_temp_entity_id: Optional[str] = None    # z.B. "sensor.tank1_water_temp"
    ha_do_entity_id: Optional[str] = None      # z.B. "sensor.tank1_dissolved_oxygen"
```

Alternativ: Tank nutzt die REQ-005 Sensor-Infrastruktur ueber eine `monitors_tank` Edge (`sensors -> tanks`).

### Seite C (Steuerung)

REQ-014 ist kein direkter Aktor-Consumer, aber es liefert **Sicherheitseingaenge** fuer REQ-018:

| Signal | REQ-018 Aktion | Mechanismus |
|--------|---------------|-------------|
| `fill_level_percent < 5%` | Bewaesserung stoppen (Trockenlaufschutz) | REQ-018 referenziert TankState als Sicherheitseingang |
| `water_temp_celsius > 22°C` | Chiller einschalten | REQ-018 `chiller` Actuator-Typ |
| `dissolved_oxygen_mgl < 4` | Air-Pump einschalten | REQ-018 `air_pump` Actuator-Typ |

**Luecke:** Diese Cross-REQ-Signale sind in REQ-018 narrativ beschrieben, aber nicht als explizite `ControlRule`-Seed-Daten definiert. Empfehlung: Seed-Rules fuer Tank-Safety:

```json
{
  "_key": "rule_tank_low_level",
  "name": "Tank Trockenlaufschutz",
  "is_safety_rule": true,
  "sensor_parameter": "tank_fill_level",
  "condition": {"operator": "lt", "threshold": 5},
  "action": {"command": "turn_off"},
  "hysteresis": {"on_threshold": 5, "off_threshold": 15, "min_on_duration_seconds": 0, "min_off_duration_seconds": 600, "cooldown_seconds": 60}
}
```

### Fehlende API-Endpoints

| Endpoint | Zweck | Consumer |
|----------|-------|----------|
| `GET /api/v1/t/{slug}/tanks/states/latest` | **Bulk-Endpoint:** Alle Tanks mit jeweils neuestem TankState in einem Call. Verhindert N+1-Problem im TankCoordinator. | TankCoordinator |
| `GET /api/v1/t/{slug}/tanks/alerts` | Aggregierte Tank-Alerts (alle Tanks). Derzeit muss `check_alerts()` Client-seitig oder pro Tank aufgerufen werden. | AlertCoordinator |
| `GET /api/v1/t/{slug}/tanks/{key}/solution-age` | Loesungsalter (temperaturkorrigiert) als dedizierter Wert | TankCoordinator (fuer Entity) |

### MQTT-Events noetig

| Topic | Payload | Begruendung |
|-------|---------|-------------|
| `kamerplanter/{tenant}/events/tank-alert` | `{tank_key, alert_type, severity, value, message}` | Tank-Leck oder pH-Crash ist zeitkritisch. 120s-Polling kann bei `severity: critical` zu langsam sein. Besonders relevant: `temperature_high_critical`, `dissolved_oxygen_critical`, `low_fill_level`. |
| `kamerplanter/{tenant}/events/tank-fill` | `{tank_key, fill_type, volume_liters, ec_ms, ph}` | Tankbefuellung triggert Aktualisierung in HA (EC/pH-Werte aendern sich schlagartig) |
| `kamerplanter/{tenant}/events/maintenance-due` | `{tank_key, maintenance_type, days_overdue}` | Faellige Wartung als Push statt ueber TaskCoordinator |

### Blueprint-Vorschlaege

**Blueprint 9: Tank DO niedrig -> Air-Pump einschalten**

```yaml
alias: "KP: Tank Sauerstoff niedrig -> Belueftung"
description: "Air-Pump einschalten wenn geloester Sauerstoff unter 6 mg/L"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_haupttank_zelt1_dissolved_oxygen
    below: 6
condition:
  - condition: state
    entity_id: switch.air_pump_tank1
    state: "off"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.air_pump_tank1
  - service: notify.mobile_app_phone
    data:
      title: "Tank: Sauerstoff niedrig"
      message: >
        Haupttank Zelt 1: DO {{ states('sensor.kp_haupttank_zelt1_dissolved_oxygen') }} mg/L.
        Air-Pump eingeschaltet. Temperatur pruefen:
        {{ states('sensor.kp_haupttank_zelt1_water_temp') }} Grad C.
mode: single
```

**Blueprint 10: Tank EC-Drift -> Korrektur-Erinnerung**

```yaml
alias: "KP: Tank EC-Abweichung"
description: "Warnung wenn Tank-EC > 20% vom Zielwert abweicht"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_haupttank_zelt1_ec_deviation_pct
    above: 20
condition: []
action:
  - service: notify.mobile_app_phone
    data:
      title: "Tank EC-Korrektur noetig"
      message: >
        EC-Abweichung {{ states('sensor.kp_haupttank_zelt1_ec_deviation_pct') }}%.
        Aktuell: {{ states('sensor.kp_haupttank_zelt1_ec') }} mS/cm.
        {% if states('sensor.kp_haupttank_zelt1_ec') | float > 2.5 %}
        EC zu hoch — Reinstwasser nachfuellen.
        {% else %}
        EC zu niedrig — Naehrstoffe nachdosieren.
        {% endif %}
mode: single
```

**Blueprint 11: Tank Loesungsalter -> Wasserwechsel-Erinnerung**

```yaml
alias: "KP: Wasserwechsel faellig"
description: "Warnung wenn Naehrloesung aelter als geplant"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_haupttank_zelt1_solution_age_days
    above: 7
condition: []
action:
  - service: notify.mobile_app_phone
    data:
      title: "Wasserwechsel faellig"
      message: >
        Haupttank Zelt 1: Naehrloesung ist {{ states('sensor.kp_haupttank_zelt1_solution_age_days') }} Tage alt.
        EC: {{ states('sensor.kp_haupttank_zelt1_ec') }} mS/cm,
        pH: {{ states('sensor.kp_haupttank_zelt1_ph') }}.
mode: single
```

---

## REQ-018: Umgebungssteuerung & Aktorik

### Status: Gut vorbereitet (4/5)

REQ-018 ist die umfangreichste Spezifikation fuer HA-Integration. Es definiert:
- 19 Aktor-Typen mit `protocol: home_assistant/mqtt/manual`
- `ha_entity_id` mit Pydantic-Validator (erzwungen bei HA-Protokoll)
- `HomeAssistantClient` mit `map_command_to_ha_service()` fuer 7 Aktor-Typen
- `ControlEngine` mit Prioritaetssystem und Hysterese
- `PhaseTransitionHandler` fuer Phasen-gebundene Steuerung
- Fail-Safe-States pro Aktor-Typ
- Konfliktgruppen (`co2_ventilation`, `heat_cool`)
- Emergency-Stop mit 3 Szenarien
- VPD-Controller als gekoppelter Regelkreis
- DLI-basierte Lichtsteuerung
- CO2-PPFD-Kopplung
- DIF/DROP-Temperatursteuerung

### Seite A (Export)

**In HA-CUSTOM-INTEGRATION.md spezifizierte Entities:**

| Entity | Quelle | Status |
|--------|--------|--------|
| `sensor.kp_{actuator}_state` | `Actuator.current_state` | OK — `current_state` auf Actuator-Dokument |

**Fehlende Entities:**

| Entity-Vorschlag | Quelle | Begruendung |
|------------------|--------|-------------|
| `sensor.kp_{actuator}_value` | `Actuator.current_value` | Dimmer-Level, Geschwindigkeit etc. `current_state` ist nur "on"/"off", der numerische Wert fehlt. |
| `sensor.kp_{actuator}_source` | `ControlEvent.event_source` (letztes Event) | Wer steuert gerade: schedule, rule, safety, manual? Fuer Dashboard: "Warum ist der Befeuchter an?" |
| `binary_sensor.kp_{actuator}_override_active` | `ManualOverride.is_active` | Override-Status als eigene Entity fuer HA-Automationen |
| `sensor.kp_{actuator}_override_expires_in` | `ManualOverride.expires_at - now()` | Countdown bis Override-Ablauf |
| `sensor.kp_{location}_control_mode` | `'modus_a'` oder `'modus_b'` pro Location/Aktor | Fuer HA: Welcher Steuerungsmodus ist aktiv? Verhindert versehentliche Doppel-Regelung. |
| `sensor.kp_{location}_dli_accumulated` | DLI-Akkumulator (REQ-018 `accumulate_dli` Celery-Task) | Fuer Modus-B: HA kann DLI-Defizit berechnen und Dimmer anpassen |
| `sensor.kp_{location}_dli_target` | `PhaseControlProfile.target_dli_mol` | Zusammen mit `dli_accumulated` fuer HA-Automationen |

### Seite B (Import)

REQ-018 importiert HA-Daten auf zwei Wegen:

1. **Sensor-Daten (indirekt ueber REQ-005):** Regelbasierte Steuerung (`ControlRule.sensor_parameter`) liest Observations aus REQ-005, die ueber `ha_entity_id` importiert werden.

2. **Aktor-Zustandsverifikation:** `HomeAssistantClient.get_entity_state()` prueft, ob der Aktor den Befehl tatsaechlich ausgefuehrt hat (`ControlEvent.success`).

| Aspekt | Status | Detail |
|--------|--------|--------|
| Aktor-Mapping | Vorhanden | `Actuator.ha_entity_id`, Validator erzwingt bei HA-Protokoll |
| Zustandsverifikation | Vorhanden | `ControlEvent.success: bool` |
| MQTT State-Topic | Vorhanden | `Actuator.mqtt_state_topic` fuer MQTT-Aktoren |
| HA-State-Polling | Vorhanden | `sync_actuator_states` Celery-Task (alle 5 Minuten) |

**Luecke B-Import:**

| # | Luecke | Detail |
|---|--------|--------|
| B-018-1 | Kein Energie-Import | `Actuator.power_watts` ist statisch. Kein dynamischer Import von HA-Energie-Sensoren (Shelly Power Monitoring). `energy_entity_id` fehlt. |
| B-018-2 | Kein Feedback-Webhook | Bei Modus B: HA steuert Aktoren selbst, aber KP weiss nicht, wann HA eine Aktion durchgefuehrt hat. `POST /api/v1/webhooks/ha-event` fehlt. |

### Seite C (Steuerung)

REQ-018 ist die **Kernspezifikation fuer Seite C**. Grenzziehung zwischen KP und HA:

**Modus A (KP steuert direkt):**

| Komponente | KP-Seite | HA-Seite |
|-----------|----------|----------|
| ControlEngine | Regel-Evaluation, Prioritaeten | Passiver Empfaenger von Service-Calls |
| HomeAssistantClient | REST API POST `/api/services/{domain}/{service}` | Fuehrt Service-Call aus |
| Zustandsverifikation | `get_entity_state()` nach Command | Liefert aktuellen State |
| Fail-Safe | Erkennung des Ausfalls | Physischer Aktor-Zustand |
| Graceful Degradation | Erzeugt REQ-006 Task | -- |

**Modus B (KP liefert Sollwerte):**

| Komponente | KP-Seite | HA-Seite |
|-----------|----------|----------|
| PhaseControlProfile | Publiziert Sollwerte als Sensor-Entities | Liest Entities, regelt Aktoren |
| VPD-Target | `sensor.kp_{plant}_vpd_target` | HA-Automation mit Hysterese |
| Photoperiode | `sensor.kp_{plant}_photoperiod` | HA-Automation Timer |
| EC-Target | `sensor.kp_{plant}_ec_target` | HA-Automation Dosierpumpe |

**Grenzziehung klar?** Teilweise. Offene Fragen:

1. **Modus-Wechsel:** Wie wird zwischen Modus A und B gewechselt? Per Aktor? Per Location? Im Backend oder in der Custom Integration? REQ-018 definiert `protocol: home_assistant/mqtt/manual`, aber kein `control_mode: modus_a/modus_b`.

2. **Hysterese-Export bei Modus B:** HA-CUSTOM-INTEGRATION.md Blueprint 2 (VPD-Regelung) hardcoded `+0.2` und `-0.1` als Hysterese-Offsets. Diese Werte kommen aus `HysteresisConfig` in REQ-018 und koennten pro Aktor/Phase variieren. Sie muessten als Entity-Attribute exportiert werden:
   - `state_attr('sensor.kp_{plant}_vpd_target', 'hysteresis_on_offset')` = 0.2
   - `state_attr('sensor.kp_{plant}_vpd_target', 'hysteresis_off_offset')` = 0.1

3. **Feedback-Loop bei Modus B:** Siehe HA-F-005 im Review. Wenn HA eine Bewaesserung ausfuehrt, muss KP davon erfahren (`WateringEvent`, `ControlEvent`). Aktuell kein Mechanismus definiert.

### Fehlende API-Endpoints

| Endpoint | Zweck | Consumer |
|----------|-------|----------|
| `GET /api/v1/t/{slug}/actuators/states` | Bulk-Endpoint: Alle Aktoren mit aktuellem State in einem Call | PlantCoordinator / LocationCoordinator (erweitert) |
| `POST /api/v1/webhooks/ha-event` | Webhook fuer HA-Callbacks bei Modus B: `{event_type: 'actuator_state_changed', entity_id, old_state, new_state, timestamp}` | HA `rest_command` oder `webhook`-Automation |
| `GET /api/v1/t/{slug}/locations/{key}/control-targets` | Aktuelle Sollwerte (VPD, Photoperiode, EC, CO2, Temperatur) einer Location als zusammengefasstes Objekt. Fuer Modus B: HA braucht alle Sollwerte in einem Call. | Custom Integration (Modus B Entity-Update) |
| `POST /api/v1/emergency-stop` | Existiert in REQ-018 narrativ, aber nicht in REST-API-Sektion als tenant-scoped Endpoint | Emergency-Stop-Button in HA (via `rest_command`) |

**Korrektur:** `POST /api/v1/emergency-stop` ist in REQ-018 erwaehnt, muesste aber tenant-scoped sein: `POST /api/v1/t/{slug}/emergency-stop`.

### MQTT-Events noetig

| Topic | Payload | Begruendung |
|-------|---------|-------------|
| `kamerplanter/{tenant}/events/actuator-command` | `{actuator_key, command, value, source, success}` | Jede Steuerungsaktion als Event — fuer HA-History und Debug |
| `kamerplanter/{tenant}/events/safety-trigger` | `{rule_key, actuator_key, sensor_reading, action}` | Sicherheitsregel hat ausgeloest — muss sofort bei HA ankommen. 30s Celery-Task-Intervall + 60s AlertCoordinator-Polling = bis zu 90s Latenz. Bei Uebertemperatur >35C inakzeptabel. |
| `kamerplanter/{tenant}/events/override-set` | `{actuator_key, override_state, override_value, expires_at, reason}` | Override wurde gesetzt/aufgehoben — HA muss sofort wissen |
| `kamerplanter/{tenant}/events/emergency-stop` | `{scenario, actuators_affected, timestamp}` | Emergency-Stop MUSS in <2s bei HA sein |
| `kamerplanter/{tenant}/events/conflict-detected` | `{conflict_group, actuators, resolution}` | Konfliktgruppen-Ausloesung (z.B. CO2 vs. Abluft) |

### Blueprint-Vorschlaege

**Blueprint 12: Emergency-Stop -> Physischer Taster**

```yaml
alias: "KP: Emergency-Stop via Taster"
description: "Physischer Notfall-Taster loest KP Emergency-Stop aus"
trigger:
  - platform: state
    entity_id: binary_sensor.emergency_button_growroom
    to: "on"
condition: []
action:
  - service: rest_command.kp_emergency_stop
    data:
      scenario: "generic"
  - service: notify.mobile_app_phone
    data:
      title: "EMERGENCY STOP"
      message: "Notfall-Taster betaetigt. Alle Aktoren in Fail-Safe-State."
      data:
        push:
          sound:
            name: "alarm.caf"
            critical: 1
            volume: 1.0
mode: single
```

```yaml
# rest_command in configuration.yaml
rest_command:
  kp_emergency_stop:
    url: "http://kamerplanter:8000/api/v1/t/default/emergency-stop"
    method: POST
    headers:
      Authorization: "Bearer kp_xxxxxxxxxxxx"
      Content-Type: "application/json"
    payload: '{"scenario": "{{ scenario }}"}'
```

**Blueprint 13: DLI-Defizit -> Dimmer anpassen (Modus B)**

```yaml
alias: "KP: DLI-Defizit Lichtanpassung"
description: "Lichtintensitaet erhoehen wenn DLI-Ziel nicht erreicht wird"
trigger:
  - platform: time
    at: "16:00"
condition:
  - condition: template
    value_template: >
      {{ states('sensor.kp_growzelt1_dli_accumulated') | float(0) <
         (states('sensor.kp_growzelt1_dli_target') | float(40) * 0.7) }}
action:
  - service: light.turn_on
    target:
      entity_id: light.growzelt_1
    data:
      brightness_pct: >
        {{ [100, (states('light.growzelt_1') | attr('brightness') | int(200)) / 255 * 100 + 15] | min | int }}
  - service: notify.mobile_app_phone
    data:
      title: "DLI-Defizit"
      message: >
        DLI um 16:00: {{ states('sensor.kp_growzelt1_dli_accumulated') }} mol/m2/d
        (Ziel: {{ states('sensor.kp_growzelt1_dli_target') }}).
        Dimmer um 15% erhoeht.
mode: single
```

---

## Konsolidierte Findings

| # | Finding | REQ | Seite | Kritikalitaet | Empfehlung |
|---|---------|-----|-------|---------------|------------|
| CF-001 | Kein Bulk-Endpoint fuer Phasen-Summaries. PlantCoordinator muss Phase, VPD-Target, EC-Target, Photoperiode aus mehreren Graph-Traversierungen zusammensetzen. | REQ-003 | A | Hoch | `GET /api/v1/t/{slug}/plants/phase-summaries` — ein Call, alle aktiven Pflanzen mit allen Sollwerten. |
| CF-002 | Phasenwechsel-Event fehlt als Push. 300s Polling kann bei Lichtprogramm-Umstellung zu 5 Minuten Verzoegerung fuehren. | REQ-003 | A | Mittel | MQTT-Topic `kamerplanter/{tenant}/events/phase-transition`. Alternativ: SSE oder WebSocket. |
| CF-003 | Graduelle Phasen-Transitionen (z.B. 18h->12h ueber 7 Tage) sind in Modus B nicht abbildbar. HA-Automationen koennen keine mehrtaegige Interpolation. | REQ-003/018 | C | Mittel | Fuer Modus B: Tages-aktuellen Interpolationswert als `sensor.kp_{plant}_photoperiod_current` exportieren. Oder: Graduelle Transitionen nur in Modus A. |
| CF-004 | Kein Bulk-Endpoint fuer TankStates. TankCoordinator braucht N+1 Calls (1 List + N states/latest). | REQ-014 | A | Hoch | `GET /api/v1/t/{slug}/tanks/states/latest` — alle Tanks mit neuestem State. |
| CF-005 | `dissolved_oxygen_mgl` und `orp_mv` im TankState-Modell vorhanden, aber nicht als HA-Entities in HA-CUSTOM-INTEGRATION.md definiert. | REQ-014 | A | Mittel | Entity-Mapping-Tabelle in HA-CUSTOM-INTEGRATION.md um `sensor.kp_{tank}_dissolved_oxygen` und `sensor.kp_{tank}_orp` erweitern. |
| CF-006 | Tank hat kein explizites `ha_entity_id`-Mapping fuer Sensoren. Verknuepfung laeuft ueber Location -> Sensor (REQ-005). | REQ-014 | B | Mittel | Optionale `ha_*_entity_id`-Felder auf Tank oder dedizierte `monitors_tank` Edge-Collection fuer Tank-spezifische Sensoren. |
| CF-007 | Safety-Regeln (Uebertemperatur, Tank-Leck) ueber Celery-Task (30s) + AlertCoordinator (60s) = bis zu 90s Latenz. Fuer Emergency-Events inakzeptabel. | REQ-018 | C | Hoch | MQTT-Echtzeit-Events fuer `safety-trigger` und `emergency-stop`. Celery-Task als Fallback, nicht als primaerer Pfad. |
| CF-008 | Modus A vs. B nicht als konfigurierbare Eigenschaft im Datenmodell. `Actuator.protocol` definiert nur HA/MQTT/manual, nicht wer die Regellogik ausfuehrt. | REQ-018 | C | Mittel | Neues Feld `Actuator.control_mode: Literal['kp_controls', 'kp_setpoint', 'manual']` — analog zu Modus A / B / manual. |
| CF-009 | Hysterese-Parameter (on_offset, off_offset) sind nicht als Entity-Attribute exportiert. Modus-B-HA-Automationen muessen Werte hardcoden. | REQ-018 | A | Mittel | VPD-Target-Entity um Attribute erweitern: `hysteresis_high`, `hysteresis_low`, `min_on_duration`, `min_off_duration`. |
| CF-010 | Webhook-Endpoint fuer Modus-B-Feedback fehlt. Wenn HA eine Bewaesserung ausfuehrt, weiss KP nichts davon. Care-Reminder zeigt weiter "Giessen faellig". | REQ-018/014 | B | Hoch | `POST /api/v1/webhooks/ha-event` mit Payload `{event_type, entity_id, action, timestamp}`. KP erstellt WateringEvent/ControlEvent aus Webhook. |
| CF-011 | `emergency-stop` Endpoint existiert nur narrativ in REQ-018 Business Case, nicht in REST-API-Endpunkte-Sektion. Kein tenant-scoped Pfad. | REQ-018 | C | Hoch | `POST /api/v1/t/{slug}/emergency-stop` explizit in API-Sektion aufnehmen mit `{scenario: 'water_leak' | 'co2_leak' | 'fire'}`. |
| CF-012 | DLI-Akkumulator (`accumulate_dli` Celery-Task) hat keinen Export-Endpoint/Entity. Modus B kann DLI-Defizit nicht nutzen. | REQ-018 | A | Mittel | `GET /api/v1/t/{slug}/locations/{key}/dli` -> `{accumulated_mol, target_mol, deficit_mol, percent_complete}`. Als Entity: `sensor.kp_{location}_dli_accumulated`. |
| CF-013 | Reconnect-Strategie bei HA-Ausfall nicht explizit definiert. REQ-005/018 definieren Fallback-Verhalten, aber kein exponentielles Backoff, keine Retry-Policy. | REQ-005/018 | B | Niedrig | `HomeAssistantConnector`: Initial 30s, Backoff bis 5 min, Alert nach 3 Fehlversuchen. Implizit durch Celery-Task-Scheduling abgedeckt, aber explizite Dokumentation wuenschenswert. |
| CF-014 | Sensor-Health-Summary fehlt als Bulk-Endpoint. AlertCoordinator muss Sensor-Offline-Status pro Sensor einzeln pruefen. | REQ-005 | A | Niedrig | `GET /api/v1/t/{slug}/sensors/health-summary` — aggregiert: online_count, offline_count, degraded_sensors[], last_update_per_location. |
| CF-015 | Control-Targets (Sollwerte einer Location) sind nicht als einzelner Endpoint verfuegbar. Modus B braucht VPD, Photoperiode, EC, CO2, Temperatur in einem Call. | REQ-018/003 | A | Mittel | `GET /api/v1/t/{slug}/locations/{key}/control-targets` — zusammengefasst aus PhaseControlProfile + aktiver Phase. |

---

## Naechste Schritte

### Prioritaet 1 (vor Custom Integration MVP)

1. **CF-001 + CF-004: Bulk-Endpoints implementieren**
   - `GET /api/v1/t/{slug}/plants/phase-summaries` (REQ-003)
   - `GET /api/v1/t/{slug}/tanks/states/latest` (REQ-014)
   - Ohne diese Endpoints muss die Custom Integration N+1-Requests machen, was bei 20+ Pflanzen und 5+ Tanks die Polling-Intervalle unrealistisch macht.

2. **CF-011: Emergency-Stop-Endpoint formalisieren**
   - `POST /api/v1/t/{slug}/emergency-stop` mit Szenario-Auswahl
   - REST-Command-Template fuer HA bereitstellen
   - Sicherheitskritisch — muss vor Aktorik-Implementierung stehen.

3. **CF-008: Control-Mode auf Actuator-Modell**
   - `control_mode: Literal['kp_controls', 'kp_setpoint', 'manual']`
   - Validierung: `control_mode='kp_controls'` erfordert `protocol != 'manual'`
   - Ohne dieses Feld kann die Custom Integration nicht zuverlaessig bestimmen, welche Entities als Sollwerte exportiert werden muessen.

### Prioritaet 2 (Custom Integration v0.2)

4. **CF-010: Webhook-Endpoint fuer Modus-B-Feedback**
   - `POST /api/v1/webhooks/ha-event`
   - Unterstuetzte Events: `watering_completed`, `actuator_state_changed`, `sensor_reading`
   - Validierung: API-Key + HMAC-Signatur (Schutz vor Replay)

5. **CF-005 + CF-009: Entity-Mapping erweitern**
   - `dissolved_oxygen` und `orp` als Tank-Entities
   - Hysterese-Parameter als Attribute auf Sollwert-Entities
   - HA-CUSTOM-INTEGRATION.md Entity-Tabelle aktualisieren

6. **CF-015: Control-Targets-Endpoint**
   - `GET /api/v1/t/{slug}/locations/{key}/control-targets`
   - Zusammengefasst: vpd_target, photoperiod, ec_target, co2_ppm, temp_day, temp_night, humidity_day, humidity_night, dli_target
   - Basis fuer Modus-B-Sollwert-Entities

### Prioritaet 3 (Langfristig)

7. **CF-002 + CF-007: MQTT-Event-Bus**
   - Topic-Struktur: `kamerplanter/{tenant}/events/{event_type}`
   - Prioritaere Events: `emergency-stop`, `safety-trigger`, `phase-transition`, `tank-alert`
   - Implementierung: Paho-MQTT-Client in Celery-Task oder Redis Pub/Sub -> MQTT-Bridge
   - Custom Integration: `MqttEventListener` neben Polling-Coordinators

8. **CF-003: Graduelle Transitionen fuer Modus B**
   - Option A: `sensor.kp_{plant}_photoperiod_current` mit tagesaktuellem Interpolationswert
   - Option B: Modus B offiziell nur fuer sofortige Sollwert-Aenderungen, graduelle Uebergaenge nur Modus A
   - Empfehlung: Option B (einfacher, klare Abgrenzung)

9. **CF-006: Tank-Sensor-Mapping**
   - Entweder direkte `ha_*_entity_id`-Felder auf Tank
   - Oder `monitors_tank` Edge-Collection (`sensors -> tanks`)
   - Entscheidung abhaengig von Implementierungsaufwand

10. **CF-012 + CF-013 + CF-014: Ergaenzende Verbesserungen**
    - DLI-Export-Endpoint
    - Reconnect-Policy dokumentieren
    - Sensor-Health-Summary-Endpoint
