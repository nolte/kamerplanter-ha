# HA-Integrationsreview: Supporting REQs (006, 007, 010, 015, 022, 023, 027)

> Erstellt: 2026-02-28
> Referenz: HA-CUSTOM-INTEGRATION.md v1.1
> Vorgaenger: spec/analysis/smart-home-ha-integration-review.md v2.0
> Methodik: Drei-Seiten-Modell (A=KP→HA Export, B=HA→KP Import, C=KP→HA Aktorik)

## Zusammenfassung

Die analysierten sieben REQs sind in der HA-CUSTOM-INTEGRATION.md v1.1 grundsaetzlich beruecksichtigt, aber mit unterschiedlicher Tiefe. Die **staerksten Abdeckungen** bestehen bei REQ-015 (Calendar-Entity via iCal, HA-006) und REQ-023 (M2M API-Keys, HA-001). Die **groessten Luecken** liegen bei:

1. **REQ-006 Aufgabenplanung:** Todo-Entity ist spezifiziert (HA-007), aber Timer-Countdowns, Training-Events, Workflow-Fortschritt und phaenologische Trigger haben keine HA-Repraesentanz.
2. **REQ-010 IPM-System:** Kein dedizierter IPM-Coordinator. Befall-Alerts, Karenz-Countdown und Hermie-Warnungen sind nicht als eigene Entities modelliert.
3. **REQ-022 Pflegeerinnerungen:** `sensor.kp_{plant}_next_watering` ist in HA-003 erwaehnt, aber die reichhaltige Care-Dashboard-Logik (10 Erinnerungstypen, Winterhaerte-Ampel, Knollen-Zyklus) wird nicht abgebildet.

Insgesamt wurden **18 Findings** identifiziert (3 hoch, 8 mittel, 7 niedrig). Die kritischste Luecke ist das Fehlen eines **MQTT-Event-Kanals fuer sicherheitsrelevante IPM-Alerts** (Hermie-Befund, kritischer Befall) — hier sind 60s Polling-Intervalle zu langsam.

---

## REQ-006: Aufgabenplanung

### Status: Teilweise abgedeckt

### Seite A (Export)

**Bereits spezifiziert in HA-CUSTOM-INTEGRATION.md:**
- `todo.kp_{location}_tasks` — Todo-Entity (HA-007), gemappt auf `GET /api/v1/t/{slug}/tasks/?status=pending`
- `TaskCoordinator` — Polling alle 300s (5 min), Minimum 120s (HA-004)
- `calendar.kp_tasks` — Calendar-Entity (HA-006), aggregiert Tasks via iCal-Feed

**Fehlende Entities:**
- `sensor.kp_{plant}_workflow_progress` — Workflow-Completion-Percentage (`WorkflowExecution.completion_percentage`). HA-Nutzer koennten Automationen triggern bei z.B. "Workflow 90% abgeschlossen → Ernte vorbereiten".
- `sensor.kp_{plant}_recovery_status` — Training-Recovery-Timer (`TrainingEvent.recovery_end_date`). Wertvoller Sensor fuer Grower die HA-Dashboards nutzen: "Tag 3/7 Erholung nach Topping".
- `sensor.kp_{plant}_next_task` — Naechste faellige Aufgabe als Sensor (Titel + Due-Date als Attribute). Einfacher als die volle Todo-Entity fuer Dashboard-Karten.
- `binary_sensor.kp_{plant}_hst_allowed` — HST-Validator-Ergebnis als Binary Sensor. Verhindert manuelle Aktionen wenn Phase das nicht erlaubt.

**Polling-Intervall:** 300s ist angemessen fuer Tasks — Aufgaben aendern sich nicht sekundengenau.

### Seite B (Import)

Keine direkte HA→KP-Datenabhaengigkeit. Tasks werden intern erzeugt (Celery, Workflow-Instantiation, CareReminderEngine).

**Indirekter Bezug:** REQ-006 definiert `PhenologicalEvent`-Trigger (z.B. Forsythienbluete → Rosen schneiden). Phaenologische Beobachtungen koennten theoretisch durch HA-Sensoren automatisiert werden (Kamera + ML-basierte Bluetenerkennung). Das ist ein Future-Feature, kein aktueller Gap.

### Seite C (Steuerung)

Keine Aktor-Relevanz. Tasks sind informativ, nicht steuernd.

**Ausnahme:** `timer_duration_seconds` auf TaskTemplate/Task (W-006). Ein HA-Timer-Helper koennte den Countdown parallel darstellen:
```yaml
# Blueprint: Task-Timer in HA synchronisieren
trigger:
  - platform: state
    entity_id: todo.kp_zelt1_tasks
    # Neuer Task mit timer_duration_seconds
action:
  - service: timer.start
    target:
      entity_id: timer.kp_task_countdown
    data:
      duration: "{{ state_attr('todo.kp_zelt1_tasks', 'active_timer_seconds') }}"
```
Dafuer fehlt aber die `timer_duration_seconds`-Information in der Todo-Entity.

### Fehlende API-Endpoints

| Endpoint | Zweck | Prioritaet |
|----------|-------|-----------|
| `GET /api/v1/t/{slug}/tasks/{task_id}/timer` | Timer-Status fuer laufende Tasks (remaining_seconds) | Niedrig |
| `GET /api/v1/t/{slug}/plants/{id}/workflow-progress` | Workflow-Completion-Percentage fuer HA-Sensor | Mittel |
| `GET /api/v1/t/{slug}/plants/{id}/training-status` | Recovery-Status + HST-Erlaubnis fuer HA-Sensor | Niedrig |

### Blueprint-Vorschlaege

| # | Blueprint | Trigger | Aktion |
|---|-----------|---------|--------|
| BP-006-1 | Task ueberfaellig → Push + Persistent Notification | `todo.kp_{location}_tasks` mit `due` < now | `notify.mobile_app` + `persistent_notification.create` |
| BP-006-2 | Workflow abgeschlossen → Benachrichtigung | `sensor.kp_{plant}_workflow_progress` = 100 | `notify.mobile_app`: "Workflow X abgeschlossen" |
| BP-006-3 | Phaenologisches Ereignis → Erinnerung | `binary_sensor.kp_phenology_forsythia` → on | `notify.mobile_app`: "Forsythie blueht — Rosen schneiden!" |

---

## REQ-007: Erntemanagement

### Status: Gut abgedeckt

### Seite A (Export)

**Bereits spezifiziert in HA-CUSTOM-INTEGRATION.md:**
- `sensor.kp_{plant}_harvest_readiness` — Readiness-Score in % (HA-003), gepollt via `PlantCoordinator` alle 300s
- `sensor.kp_{plant}_karenz_remaining` — Verbleibende Karenz-Tage (HA-003), berechenbar aus Treatment-Applications
- Blueprint 3: "Erntebereitschaft → Push-Benachrichtigung" (HA-CUSTOM-INTEGRATION.md §4)

**Fehlende Entities:**
- `sensor.kp_{plant}_trichome_stage` — Aktuelles Trichom-Stadium (immature/approaching/peak/overripe). Fuer Cannabis-Grower wertvoller als der nackte %-Score. Koennte als Attribut auf `harvest_readiness` exponiert werden.
- `sensor.kp_{plant}_estimated_harvest_date` — Geschaetztes Erntedatum (`avg_days_to_harvest` aus der Multi-Indicator-Aggregation). Fuer HA-Kalender-Automation nuetzlich.
- `binary_sensor.kp_{plant}_flushing_active` — Ob ein Flushing-Protokoll aktiv ist. Relevant fuer Automatisierung: "Wenn Flushing aktiv → EC-Zielwert auf 0 setzen".
- `sensor.kp_{plant}_flushing_day` — Tag X von Y im Flushing-Protokoll (z.B. "Tag 7/14").

**Polling-Intervall:** 300s ist angemessen — Erntebereitschaft aendert sich im Stunden-/Tagesbereich, nicht sekundlich.

### Seite B (Import)

Keine direkte HA→KP-Datenabhaengigkeit. Die `harvest_observations` werden manuell erfasst (Trichom-Mikroskopie, Brix-Messung).

**Indirekter Bezug:** REQ-007 definiert `HarvestEnvironment` (Temperatur, Luftfeuchte zum Erntezeitpunkt). Diese Daten koennten automatisch aus HA-Sensoren uebernommen werden:
- `sensor.growzelt_temperature` → `harvest_environment.temperature_celsius`
- `sensor.growzelt_humidity` → `harvest_environment.humidity_percent`

Dafuer fehlt ein Mechanismus, der bei Batch-Erstellung automatisch die aktuellen HA-Sensorwerte eintraegt. Aktuell: manuelle Eingabe.

### Seite C (Steuerung)

**Flushing-Automatisierung:**
Wenn ein Flushing-Protokoll gestartet wird (REQ-007 AQL "Flushing-Trigger"), sollte im Modus A die Duenge-Dosierung auf 0 gesetzt werden:
```yaml
# Blueprint: Flushing gestartet → Dosierpumpe deaktivieren
trigger:
  - platform: state
    entity_id: binary_sensor.kp_white_widow_flushing_active
    to: "on"
action:
  - service: switch.turn_off
    target:
      entity_id: switch.dosierpumpe_a
  - service: switch.turn_off
    target:
      entity_id: switch.dosierpumpe_b
```

**Dark-Period-Automatisierung:**
Pre-Harvest Dark Period (24-48h vor Ernte, REQ-007 §1) benoetigt Lichtabschaltung:
```yaml
# Blueprint: Dark Period → Licht aus
trigger:
  - platform: state
    entity_id: sensor.kp_white_widow_harvest_readiness
    # Attribut: pre_harvest_protocol == 'dark_period'
action:
  - service: light.turn_off
    target:
      entity_id: light.growzelt_1
```

### Fehlende API-Endpoints

| Endpoint | Zweck | Prioritaet |
|----------|-------|-----------|
| `GET /api/v1/t/{slug}/plants/{id}/harvest-readiness` | Dedizierter Readiness-Endpoint fuer HA (existiert ggf. bereits) | Mittel |
| `GET /api/v1/t/{slug}/plants/{id}/flushing-status` | Flushing aktiv/Tag/Dauer fuer HA-Sensor | Mittel |
| `GET /api/v1/t/{slug}/plants/{id}/pre-harvest-status` | Aggregierter Pre-Harvest-Status (Flushing + Dark Period + Karenz) | Mittel |

### Blueprint-Vorschlaege

| # | Blueprint | Trigger | Aktion |
|---|-----------|---------|--------|
| BP-007-1 | Flushing gestartet → Dosierpumpe aus | `binary_sensor.kp_{plant}_flushing_active` → on | `switch.turn_off` (Dosierpumpe A+B) |
| BP-007-2 | Dark Period → Licht aus | `sensor.kp_{plant}_pre_harvest_protocol` = "dark_period" | `light.turn_off` (Growlicht) |
| BP-007-3 | Ernte in 3 Tagen → Vorbereitungs-Erinnerung | `sensor.kp_{plant}_estimated_harvest_date` = today + 3d | `notify.mobile_app`: "Ernte-Equipment vorbereiten" |

---

## REQ-010: IPM-System

### Status: Unzureichend abgedeckt

### Seite A (Export)

**Bereits spezifiziert in HA-CUSTOM-INTEGRATION.md:**
- `sensor.kp_{plant}_health_score` — Aggregierter IPM + Quality-Score in % (HA-003), gepollt via `PlantCoordinator` alle 300s
- `binary_sensor.kp_{plant}_needs_attention` — Alerts + ueberfaellige Tasks (HA-003), gepollt via `AlertCoordinator` alle 60s

**Fehlende Entities:**
- `sensor.kp_{plant}_pest_pressure` — Aktueller Befallsdruck (none/low/medium/high/critical) aus der letzten Inspektion. Wertvoller als der aggregierte `health_score` fuer gezielte Automationen.
- `sensor.kp_{plant}_karenz_remaining` — Bereits in HA-003 definiert, aber die **Datenquelle ist unklar**: Der `PlantCoordinator` pollt `GET /plants/`, aber Karenz-Berechnung erfordert `treatment_applications`-Daten. Entweder muss der Plant-Endpoint die Karenz-Info mitliefern, oder ein separater Endpoint ist noetig.
- `binary_sensor.kp_{plant}_karenz_active` — Ob aktuell eine Karenzzeit laeuft (einfacher als Tage-Countdown fuer Automationen).
- `sensor.kp_{location}_last_inspection_days` — Tage seit letzter Inspektion pro Location. Fuer Automationen: "Wenn >7 Tage → Erinnerung".
- `binary_sensor.kp_{plant}_hermie_detected` — Hermaphrodismus-Befund als sofortiger Alert. **Kritisch**: Bei `severity: critical` und `estimated_pollen_release: true` muss HA sofort reagieren koennen (Isolation, Benachrichtigung).
- `sensor.kp_{plant}_resistance_warning` — Wirkstoff-Rotations-Warnung (ResistanceManager: >3 Anwendungen desselben Wirkstoffs in 90 Tagen).

**Polling-Intervall:** 60s fuer Alerts ist angemessen fuer Standard-IPM. Fuer Hermaphrodismus-Befunde mit `estimated_pollen_release: true` waere ein **Push-Event via MQTT** ideal (HA-F-001 aus dem Review).

### Seite B (Import)

**Umgebungsdaten fuer Risiko-Modelle:**
REQ-010 definiert `environmental_conditions: dict[str, float]` (temp_c, humidity_percent, vpd_kpa) auf `InspectionRecord`. Diese Daten kommen typischerweise von HA-Sensoren (REQ-005). Der Sensor-Import ist in REQ-005 bereits abgedeckt, aber:

- **Fehlende automatische Korrelation:** Wenn HA `sensor.growzelt_humidity` > 80% meldet und REQ-010 weiss, dass >80% rH ein Mehltau-Risiko darstellt, sollte das System automatisch eine erhoehte Inspektionsfrequenz triggern. Dafuer braucht das KP-Backend den aktuellen Sensor-Wert — dieser kommt via REQ-005 `HomeAssistantConnector`.
- **Stress-Korrelation bei Hermie:** `HermaphroditismFinding.stress_correlation` kann `heat_stress` (>30°C), `light_leak` sein. HA-Sensoren koennten diese automatisch vorschlagen: Wenn `sensor.growzelt_temperature` > 30°C in den letzten 48h → `stress_correlation: heat_stress` vorausfuellen.

### Seite C (Steuerung)

**Keine direkte Aktor-Relevanz.** IPM ist primaer dokumentarisch (Inspektionen, Behandlungen).

**Indirekte Aktor-Relevanz:**
- Bei Mehltau-Warnung (rH >80%) → HA-Automation: Entfeuchter einschalten (Modus B: KP meldet Risiko, HA regelt)
- Bei Hermie-Befund `severity: critical` → HA-Automation: Lichtleck-Check ausloesen (z.B. Dimmer auf 0% testen ob noch Licht durchkommt)

### Fehlende API-Endpoints

| Endpoint | Zweck | Prioritaet |
|----------|-------|-----------|
| `GET /api/v1/t/{slug}/plants/{id}/ipm-status` | Aggregierter IPM-Status (Befallsdruck, Karenz, letzte Inspektion, Hermie-Status) fuer HA-Sensor | Hoch |
| `GET /api/v1/t/{slug}/alerts/?type=ipm` | IPM-spezifische Alerts filtern (Befall, Karenz, Hermie) | Mittel |
| `GET /api/v1/t/{slug}/plants/{id}/karenz-status` | Dedizierter Karenz-Endpoint (aktive Karenzzeiten + Resttage) | Mittel |

### MQTT-Events (Push statt Polling)

| Event | Topic | Payload | Begruendung |
|-------|-------|---------|-------------|
| Hermie-Befund (critical) | `kamerplanter/{tenant}/events/ipm/hermie_critical` | `{plant_key, severity, estimated_pollen_release, timestamp}` | Pollenfreisetzung erfordert Sofortreaktion (<60s) |
| Befall-Alarm (high/critical) | `kamerplanter/{tenant}/events/ipm/pest_alert` | `{plant_key, pest_name, pressure_level, timestamp}` | Schnelle Benachrichtigung fuer Schaedlingsbekaempfung |
| Karenz-Start | `kamerplanter/{tenant}/events/ipm/karenz_started` | `{plant_key, ingredient, days, safe_until}` | Informativ, aber relevant fuer Ernte-Automationen |

### Blueprint-Vorschlaege

| # | Blueprint | Trigger | Aktion |
|---|-----------|---------|--------|
| BP-010-1 | Hermie critical → Notfall-Benachrichtigung | MQTT `ipm/hermie_critical` oder `binary_sensor.kp_{plant}_hermie_detected` | `notify.mobile_app` (critical channel) + `persistent_notification.create` |
| BP-010-2 | Hohe Luftfeuchte → Mehltau-Warnung | `sensor.growzelt_humidity` > 80% fuer >2h | `notify.mobile_app`: "Mehltau-Risiko! Inspizieren und entfeuchten." |
| BP-010-3 | Karenz abgelaufen → Ernte freigegeben | `binary_sensor.kp_{plant}_karenz_active` → off | `notify.mobile_app`: "Karenz abgelaufen — Ernte moeglich" |

---

## REQ-015: Kalenderansicht

### Status: Sehr gut abgedeckt

### Seite A (Export)

**Bereits spezifiziert in HA-CUSTOM-INTEGRATION.md:**
- `calendar.kp_tasks` — Calendar-Entity via iCal-Feed (HA-006)
- Endpoint: `GET /api/v1/calendar/feeds/{feed_id}/feed.ics?token={token}` — Token-basiert, kein JWT noetig
- REQ-015 §4.2 dokumentiert explizit die HA-Integration (Config Flow Feed-Auswahl, Generic Calendar Platform als Alternative)
- `CalendarCoordinator` — iCal-Feed-Polling (HA-004)

**Fehlende Entities:**
- `calendar.kp_{location}_tasks` — Standort-spezifischer Kalender (ein Feed pro Location). Aktuell: ein globaler Feed. Fuer HA-Power-User mit mehreren Zonen (2 Zelte + Gewaechshaus) sind separate Kalender pro Location sinnvoll.

**Gut geloest:**
- Token-basierte Auth umgeht JWT-Problematik vollstaendig
- `webcal://` URL funktioniert sowohl in HA als auch in Thunderbird/Apple Calendar/Google Calendar
- RFC 5545-konformer iCal-Output mit VALARM, COLOR, X-APPLE-CALENDAR-COLOR
- `include_timeline`-Filter erlaubt Kontrolle ueber historische Events
- Farbkodierung per Kategorie wird von Apple Calendar und einigen HA-Frontends unterstuetzt

**REQ-015 Outdoor-Erweiterungen (v1.2):**
- Aussaatkalender-Modus und Saisonuebersicht sind reine Frontend-Ansichten — keine HA-Relevanz
- Frost-Kalender-Konfiguration (`last_frost_date`, `first_frost_date`) koennte als HA-Sensor exponiert werden: `sensor.kp_{site}_first_frost_date`

### Seite B (Import)

Keine HA→KP-Datenabhaengigkeit. Kalender-Events werden aus internen KP-Daten aggregiert.

### Seite C (Steuerung)

Keine Aktor-Relevanz. Kalender ist informativ.

### Fehlende API-Endpoints

Keine — REQ-015 API ist fuer HA vollstaendig. Der iCal-Endpoint mit Token-Auth ist exakt das, was die Custom Integration braucht.

### Blueprint-Vorschlaege

| # | Blueprint | Trigger | Aktion |
|---|-----------|---------|--------|
| BP-015-1 | Naechstes Kalender-Event → Dashboard-Karte | `calendar.kp_tasks` `event` property | Lovelace: Calendar-Card mit Kamerplanter-Events |
| BP-015-2 | Morgen-Briefing → TTS-Zusammenfassung | `time` trigger 07:00 + `calendar.kp_tasks.async_get_events(today, today)` | `tts.speak`: "Heute 3 Aufgaben: Topping White Widow, Duengung Zelt 2, IPM-Inspektion" |

---

## REQ-022: Pflegeerinnerungen

### Status: Teilweise abgedeckt

### Seite A (Export)

**Bereits spezifiziert in HA-CUSTOM-INTEGRATION.md:**
- `sensor.kp_{plant}_next_watering` — Naechste Giess-Erinnerung aus `GET /care-reminders/` (HA-003), gepollt via `PlantCoordinator` alle 300s

**Fehlende Entities:**
- `sensor.kp_{plant}_care_style` — Aktueller Care-Style (tropical/succulent/orchid/...) als Attribut oder eigener Sensor. Fuer HA-Automationen: "Wenn care_style == cactus → Bewaesserung nur alle 21 Tage".
- `sensor.kp_{plant}_watering_interval` — Effektives Giessintervall (inkl. saisonaler Anpassung + Adaptive Learning). Fuer Modus-B-Automationen: HA liest Intervall und steuert Bewaesserungsventil.
- `binary_sensor.kp_{plant}_watering_due` — Ob Giessen faellig ist (einfacher als Datum-Parsing fuer HA-Automationen).
- `binary_sensor.kp_{plant}_fertilizing_due` — Ob Duengung faellig ist.
- `sensor.kp_{plant}_days_since_watering` — Tage seit letzter Bestaetigung (fuer Dashboard).
- `sensor.kp_{plant}_hardiness_rating` — Winterhaerte-Ampel (hardy/needs_protection/frost_free/dig_and_store). Relevant fuer Outdoor-Grower mit HA-Wetter-Integration.
- `binary_sensor.kp_{plant}_winter_protection_needed` — Fuer Frostschutz-Automationen (REQ-022 §2 OverwinteringProfile).
- `sensor.kp_{plant}_tuber_status` — Knollen-Zyklus-Status (planted/growing/dig_pending/drying/stored/pre_sprouting). Fuer Dahliengaertner relevant.

**Polling-Intervall:** 300s ist angemessen — Pflegeerinnerungen aendern sich im Tagesrhythmus.

**Care-Dashboard fuer HA:**
Das gesamte Care-Dashboard (REQ-022 §4, `GET /dashboard`) mit allen 10 Erinnerungstypen und Dringlichkeits-Sortierung waere als dedizierter Coordinator wertvoll. Aktuell sind Care-Reminders nur als `next_watering` im `PlantCoordinator` enthalten.

### Seite B (Import)

**HA-Sensoren fuer adaptive Giessintervalle:**
REQ-022 definiert `winter_watering_multiplier` basierend auf Kalendermonaten. Mit HA-Sensorik koennte das System praeziser arbeiten:
- `sensor.wohnzimmer_temperature` → Niedrige Raumtemperatur korreliert mit geringerem Wasserbedarf
- `sensor.wohnzimmer_humidity` → Hohe Heizungs-Trockenheit erhoet Verdunstung (Gegeneffekt zum Winter-Multiplikator)
- `sensor.outdoor_temperature` → Fuer Outdoor-Pflanzen: automatische Giessintervall-Anpassung bei Hitzewelle

Aktuell: CareReminderEngine nutzt nur den statischen `winter_watering_multiplier` aus dem CareProfile. Eine HA-basierte dynamische Anpassung waere ein wertvolles Future-Feature.

**Frost-Warnung fuer Ueberwinterung:**
REQ-022 §2 definiert `OverwinteringProfile` mit `winter_action_month`. Mit HA-Wetter-Integration (REQ-005) koennte das System den tatsaechlichen ersten Frost statt des statischen Kalendermonats verwenden:
- `sensor.openweathermap_forecast_temperature` < 3°C → `tuber_status: dig_pending` triggern

### Seite C (Steuerung)

**Bewaesserungs-Automatisierung (Modus B):**
REQ-022 liefert die *wann*-Information, HA steuert das *wie*:
```yaml
# Blueprint: Giessen faellig → Bewaesserungsventil oeffnen
trigger:
  - platform: state
    entity_id: binary_sensor.kp_monstera_watering_due
    to: "on"
condition:
  - condition: state
    entity_id: input_boolean.auto_watering_enabled
    state: "on"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.bewaesserungsventil_wohnzimmer
    data: {}
  - delay: "00:05:00"
  - service: switch.turn_off
    target:
      entity_id: switch.bewaesserungsventil_wohnzimmer
```

**Frostschutz-Automatisierung:**
```yaml
# Blueprint: Winterschutz noetig → Heizung an
trigger:
  - platform: state
    entity_id: binary_sensor.kp_oleander_winter_protection_needed
    to: "on"
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.wintergarten
    data:
      temperature: 8
```

### Fehlende API-Endpoints

| Endpoint | Zweck | Prioritaet |
|----------|-------|-----------|
| `GET /api/v1/t/{slug}/care-reminders/ha-summary` | Kompakter Summary-Endpoint fuer HA: pro Pflanze `{watering_due, fertilizing_due, days_since_watering, care_style, effective_interval}` | Hoch |
| `POST /api/v1/t/{slug}/care-reminders/plants/{key}/confirm` | Bestaetigung via HA-Service (nach automatischer Bewaesserung im Modus B: HA bestaetigt → KP aktualisiert Intervall) | Hoch |
| `GET /api/v1/t/{slug}/plants/{id}/overwintering-status` | Winterhaerte-Ampel + Knollen-Status fuer HA-Sensor | Mittel |

### MQTT-Events (Push statt Polling)

| Event | Topic | Payload | Begruendung |
|-------|-------|---------|-------------|
| Giessen ueberfaellig (>3 Tage) | `kamerplanter/{tenant}/events/care/watering_overdue` | `{plant_key, days_overdue, care_style}` | Push statt 5-min-Polling fuer zeitkritische Erinnerungen |
| Knollen-Status-Wechsel | `kamerplanter/{tenant}/events/care/tuber_status_changed` | `{plant_key, old_status, new_status}` | Saisonale Zustandswechsel sind selten, aber wichtig |

### Blueprint-Vorschlaege

| # | Blueprint | Trigger | Aktion |
|---|-----------|---------|--------|
| BP-022-1 | Giessen faellig → Bewaesserungsventil (Modus B) | `binary_sensor.kp_{plant}_watering_due` → on | `switch.turn_on` Ventil + Timer + `switch.turn_off` |
| BP-022-2 | Giessen ueberfaellig → Push-Alarm | `sensor.kp_{plant}_days_since_watering` > Intervall + 2 | `notify.mobile_app`: "Monstera seit 10 Tagen nicht gegossen!" |
| BP-022-3 | Frost-Warnung → Ueberwinterungs-Check | `weather.home` Forecast < 3°C + `sensor.kp_{plant}_hardiness_rating` != "hardy" | `notify.mobile_app`: "Frost in 2 Tagen — 3 Pflanzen einraeumen!" |
| BP-022-4 | Automatische Bewaesserung → KP bestaetigen | `switch.bewaesserungsventil` → off (nach Bewaesserung) | `rest_command.kp_confirm_watering` (POST confirm) |

---

## REQ-023: Benutzerverwaltung & Authentifizierung

### Status: Sehr gut abgedeckt

### Seite A (Export)

**Bereits spezifiziert in HA-CUSTOM-INTEGRATION.md:**
- HA-001 Config Flow Step 2: Auth-Konfiguration mit drei Optionen:
  - Option A: Light-Modus (kein Auth) → Skip
  - Option B: API-Key (`kp_...`, REQ-023 §3.7) → Empfohlen
  - Option C: Username/Password → `POST /api/v1/auth/login` → JWT
- Bearer-Erkennung: `kp_...` → API-Key-Lookup, `eyJ...` → JWT-Validierung (REQ-023 §3.7)
- Rate Limit: 1000 req/min fuer API-Keys (REQ-023 §3.7)
- HA-008 Diagnostics: `api_key_prefix` wird angezeigt (erste 8 Zeichen)

**Gut geloest:**
- M2M API-Keys sind exakt fuer den HA-Use-Case designed
- `kp_`-Prefix erlaubt automatische Unterscheidung von JWTs
- SHA-256-Hash-Speicherung ist sicher
- `tenant_scope` auf ApiKey erlaubt pro-Tenant-Keys (Config Flow Step 3)
- Revocation ist sofort wirksam → Key-Rotation ohne Downtime
- `last_used_at` Tracking fuer Monitoring

**Fehlende Aspekte:**
- **API-Key-Erstellung via Config Flow:** Der aktuelle Config Flow (HA-001) erwartet, dass der API-Key bereits existiert. Es waere nutzerfreundlich, wenn der Config Flow direkt einen Key erstellen koennte (via `POST /api/v1/auth/api-keys`). Dafuer muesste Step 2 einen "Key erstellen"-Sub-Flow haben, der Username/Password nutzt um einen API-Key zu generieren.
- **Key-Expiry:** REQ-023 §3.7 definiert kein Ablaufdatum fuer API-Keys. Fuer Sicherheit empfehlenswert: Optionales `expires_at` auf ApiKey, damit Keys nicht ewig gueltig sind. HA-CUSTOM-INTEGRATION.md koennte bei Diagnostics warnen: "API-Key aelter als 1 Jahr — Rotation empfohlen".

### Seite B (Import)

Keine HA→KP-Datenabhaengigkeit im Auth-Kontext.

### Seite C (Steuerung)

Keine Aktor-Relevanz.

### Fehlende API-Endpoints

| Endpoint | Zweck | Prioritaet |
|----------|-------|-----------|
| `GET /api/health` | Health-Check fuer Config Flow (HA-001 referenziert dies — Endpoint muss existieren und `{"status": "healthy", "version": "..."}` zurueckgeben) | Hoch |
| `POST /api/v1/auth/api-keys` via Basic Auth | Key-Erstellung ohne bestehenden JWT (fuer Config Flow: User gibt Username/Password ein, Flow erstellt automatisch Key) | Mittel |

### Blueprint-Vorschlaege

Keine — Auth ist Infrastruktur, keine Automatisierungsquelle.

---

## REQ-027: Light-Modus

### Status: Sehr gut abgedeckt

### Seite A (Export)

**Bereits spezifiziert in HA-CUSTOM-INTEGRATION.md:**
- HA-001 Config Flow Step 2 Option A: Light-Modus-Erkennung → Auth-Skip
- `GET /api/v1/mode` → `{"mode": "light", "features": {"auth": false, ...}}` (REQ-027 §6.3)
- `GET /api/health` liefert `server_mode` fuer HA-002 Device Registry
- HA-008 Diagnostics: `kamerplanter_mode: "light"` oder `"full"`

**Gut geloest:**
- Light-Modus ist der **ideale Use-Case fuer HA-Integration**: Kamerplanter auf Raspberry Pi im LAN, HA auf demselben Netzwerk, kein Auth-Overhead
- System-Tenant `mein-garten` ist deterministisch → HA Config Flow kann im Light-Modus direkt `tenant_slug: "mein-garten"` setzen (Step 3 ueberspringen)
- `LightAuthProvider` akzeptiert Requests ohne Authorization-Header → HA-Custom-Integration braucht im Light-Modus keinen API-Key

**Fehlende Aspekte:**
- **Config Flow Light-Modus-Erkennung:** HA-001 Step 2 beschreibt Light-Modus als manuelle Option ("Kein Auth noetig → Skip"). Besser: Config Flow ruft `GET /api/v1/mode` auf und erkennt Light-Modus automatisch → Steps 2 und 3 werden automatisch uebersprungen.
- **Sicherheitswarnung in HA:** Wenn die KP-URL nicht `localhost` oder private IP ist und Mode=light, sollte die HA-Integration eine persistente Warnung anzeigen (analog REQ-027 §11).

### Seite B (Import)

Keine Abhaengigkeit.

### Seite C (Steuerung)

Keine Abhaengigkeit.

### Fehlende API-Endpoints

Keine — `GET /api/v1/mode` ist ausreichend.

### Blueprint-Vorschlaege

Keine — Light-Modus ist eine Deployment-Konfiguration, keine Automatisierungsquelle.

---

## Konsolidierte Findings

| # | Finding | REQ | Seite | Kritikalitaet | Empfehlung |
|---|---------|-----|-------|---------------|------------|
| SF-001 | Kein dedizierter IPM-Status-Endpoint fuer HA — Befallsdruck, Karenz, Hermie-Status muessen aus verschiedenen Quellen aggregiert werden. `health_score` ist zu undifferenziert. | REQ-010 | A | Hoch | Neuer Endpoint `GET /api/v1/t/{slug}/plants/{id}/ipm-status` der `pest_pressure`, `karenz_remaining`, `karenz_active`, `hermie_detected`, `last_inspection_days` aggregiert. Alternativ: Attribute auf `sensor.kp_{plant}_health_score` erweitern. |
| SF-002 | Hermie-Befund (critical) hat keinen Push-Kanal — 60s Polling-Intervall ist zu langsam fuer Pollenfreisetzungs-Notfaelle. | REQ-010 | A | Hoch | MQTT-Event `kamerplanter/{tenant}/events/ipm/hermie_critical` bei Erstellung eines `HermaphroditismFinding` mit `severity: critical`. Komplementiert HA-F-001 aus dem bestehenden Review. |
| SF-003 | Care-Reminder-Summary-Endpoint fehlt — `PlantCoordinator` hat nur `next_watering`, aber nicht die volle Care-Dashboard-Logik (10 Typen, Dringlichkeit, Winterhaerte). | REQ-022 | A | Hoch | Neuer Endpoint `GET /api/v1/t/{slug}/care-reminders/ha-summary` mit kompakter Struktur pro Pflanze. Alternativ: Dedizierter `CareCoordinator` in der Custom Integration (neben den 5 bestehenden). |
| SF-004 | Keine HA-Bestaetigung nach automatischer Bewaesserung — Im Modus B (HA regelt) weiss KP nicht, dass gegossen wurde. Care-Reminder bleibt auf "faellig". | REQ-022 | B | Mittel | Webhook-Endpoint `POST /api/v1/t/{slug}/care-reminders/plants/{key}/confirm` fuer HA-Callbacks. Alternativ via HA-Service → `rest_command` in HA. Korrespondiert mit HA-F-005 aus dem bestehenden Review. |
| SF-005 | Flushing/Dark-Period-Status hat keine HA-Entity — REQ-007 Pre-Harvest-Protokolle sind fuer HA-Automationen unsichtbar. | REQ-007 | A | Mittel | `binary_sensor.kp_{plant}_flushing_active` + `sensor.kp_{plant}_flushing_day` als Entities im PlantCoordinator. Backend: `GET /plants/{id}/pre-harvest-status`. |
| SF-006 | Workflow-Fortschritt hat keine HA-Entity — `WorkflowExecution.completion_percentage` ist fuer HA unsichtbar. | REQ-006 | A | Mittel | `sensor.kp_{plant}_workflow_progress` im PlantCoordinator. Backend-Daten existieren bereits (`WorkflowExecution.completion_percentage`). |
| SF-007 | Calendar-Entity nur global, nicht pro Location — HA-Power-User mit mehreren Zonen brauchen separate Kalender. | REQ-015 | A | Mittel | Mehrere CalendarFeeds (einer pro Location) in Config Flow Step 4 anbieten. Backend unterstuetzt dies bereits (Feed-Filter `location_ids`). Nur Custom-Integration-Anpassung noetig. |
| SF-008 | Winterhaerte-Ampel hat keine HA-Entity — `OverwinteringProfile.hardiness_rating` ist fuer Frostschutz-Automationen unsichtbar. | REQ-022 | A | Mittel | `sensor.kp_{plant}_hardiness_rating` + `binary_sensor.kp_{plant}_winter_protection_needed` als saisonale Entities. |
| SF-009 | API-Key-Erstellung im Config Flow nicht moeglich — User muss Key vorab in KP-UI erstellen. | REQ-023 | A | Mittel | Config Flow Sub-Step: Username/Password eingeben → `POST /auth/login` → JWT → `POST /auth/api-keys` → Key speichern → Key fuer alle weiteren Requests nutzen. |
| SF-010 | Config Flow erkennt Light-Modus nicht automatisch — User muss manuell "Light-Modus" waehlen. | REQ-027 | A | Mittel | Config Flow Step 1: Nach URL-Validierung `GET /api/v1/mode` aufrufen. Bei `mode: light` → Steps 2+3 automatisch ueberspringen, `tenant_slug: "mein-garten"` setzen. |
| SF-011 | `GET /api/health` Endpoint ist in HA-001 referenziert aber nicht explizit in einem REQ spezifiziert. | REQ-023 | A | Mittel | Health-Endpoint in NFR-007 (Betriebsstabilitaet) oder REQ-023 formalisieren: `GET /api/health` → `{"status": "healthy", "version": "1.0.0", "mode": "full|light"}`. |
| SF-012 | Training-Recovery-Timer hat keine HA-Entity — `TrainingEvent.recovery_end_date` ist fuer HA unsichtbar. | REQ-006 | A | Niedrig | `sensor.kp_{plant}_recovery_status` mit Attributen `recovery_day`, `recovery_total_days`, `recovery_end_date`. Nur fuer Cannabis-/Nutzpflanzen-Grower relevant. |
| SF-013 | Trichom-Stadium hat keine dedizierte HA-Entity — nur aggregierter `harvest_readiness` %-Score. | REQ-007 | A | Niedrig | `sensor.kp_{plant}_trichome_stage` (immature/approaching/peak/overripe) als Attribut auf `harvest_readiness`. |
| SF-014 | Geschaetztes Erntedatum hat keine HA-Entity. | REQ-007 | A | Niedrig | `sensor.kp_{plant}_estimated_harvest_date` (ISO-Datum) als Attribut auf `harvest_readiness`. |
| SF-015 | Knollen-Zyklus-Status hat keine HA-Entity. | REQ-022 | A | Niedrig | `sensor.kp_{plant}_tuber_status` (planted/growing/dig_pending/drying/stored/pre_sprouting). Nur fuer Dahliengaertner relevant. |
| SF-016 | Timer-Information (timer_duration_seconds) fehlt in Todo-Entity. | REQ-006 | A | Niedrig | `timer_duration_seconds` und `timer_label` als Attribute auf `TodoItem` in der Todo-Entity. |
| SF-017 | Harvest-Environment nicht automatisch aus HA-Sensoren befuellt. | REQ-007 | B | Niedrig | Backend: Bei Batch-Erstellung optional HA-Sensorwerte automatisch eintragen (`temperature_celsius`, `humidity_percent` aus `HomeAssistantConnector`). |
| SF-018 | API-Key ohne Ablaufdatum — Sicherheitsempfehlung. | REQ-023 | A | Niedrig | Optionales `expires_at` auf ApiKey. HA-Diagnostics: Warnung bei Keys aelter als 365 Tage. |

---

## Optionalitaets-Checkliste

Alle analysierten REQs funktionieren **vollstaendig ohne HA**:

| REQ | Feature | Ohne HA nutzbar? | Manueller Fallback |
|-----|---------|:----------------:|-------------------|
| REQ-006 | Aufgabenplanung | Ja | Tasks in KP-UI verwalten, kein HA-Dashboard noetig |
| REQ-007 | Erntemanagement | Ja | Readiness-Check, Flushing, Batch-Tracking rein in KP |
| REQ-010 | IPM-System | Ja | Inspektionen, Behandlungen, Karenz-Gate rein in KP |
| REQ-015 | Kalenderansicht | Ja | FullCalendar in KP-Frontend + iCal-Export in Thunderbird/Apple/Google |
| REQ-022 | Pflegeerinnerungen | Ja | Care-Dashboard in KP-Frontend, Celery generiert Tasks serverseitig |
| REQ-023 | Benutzerverwaltung | Ja | JWT-Auth funktioniert ohne HA. API-Keys sind optional. |
| REQ-027 | Light-Modus | Ja | Light-Modus ist HA-unabhaengig. HA profitiert davon (kein Auth-Overhead). |

---

## Naechste Schritte

### Prioritaet 1 (Vor Custom-Integration-MVP)

1. **`GET /api/health` formalisieren** (SF-011) — Wird von Config Flow (HA-001) benoetigt. Muss `status`, `version`, `mode` zurueckgeben. Implementierungsaufwand: ~20 Zeilen.

2. **Config-Flow-Auto-Detect fuer Light-Modus** (SF-010) — `GET /api/v1/mode` im Config Flow auswerten. Reine Custom-Integration-Aenderung, kein Backend-Aufwand.

3. **IPM-Status-Aggregations-Endpoint** (SF-001) — `GET /api/v1/t/{slug}/plants/{id}/ipm-status`. Aggregiert Befallsdruck, Karenz, Hermie-Status, letzte Inspektion. Backend-Aufwand: ~100 Zeilen (AQL + Service + Router).

### Prioritaet 2 (Custom-Integration v0.2)

4. **Care-Reminder-HA-Summary** (SF-003) — Kompakter Endpoint fuer einen dedizierten `CareCoordinator`. Backend: ~80 Zeilen. Custom Integration: neuer Coordinator.

5. **Flushing/Pre-Harvest-Status** (SF-005) — `GET /plants/{id}/pre-harvest-status`. Backend: ~60 Zeilen. Custom Integration: Attribut auf PlantCoordinator.

6. **Config-Flow API-Key-Erstellung** (SF-009) — Sub-Flow in Config Flow Step 2. Reine Custom-Integration-Aenderung.

7. **Care-Confirmation via REST** (SF-004) — `POST /care-reminders/plants/{key}/confirm` fuer HA-Callbacks nach Modus-B-Bewaesserung. Korrespondiert mit HA-F-005.

### Prioritaet 3 (Custom-Integration v0.3+)

8. **MQTT-Event-Kanal fuer IPM-Alerts** (SF-002) — Erfordert MQTT-Publisher im Backend (Celery-Task mit Paho-Client). Korrespondiert mit HA-F-001. Mittlerer Aufwand.

9. **Zusaetzliche Entities** (SF-006, SF-007, SF-008, SF-012–SF-016) — Schrittweise Erweiterung des Entity-Registries in der Custom Integration. Pro Entity: ~30 Zeilen Python.

10. **API-Key-Expiry** (SF-018) — Optionales `expires_at` Feld auf ApiKey. Niedriger Aufwand, gute Sicherheitshygiene.
