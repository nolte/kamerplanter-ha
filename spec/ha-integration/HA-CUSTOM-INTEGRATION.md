# Spezifikation: Home Assistant Custom Integration (kamerplanter-ha)

```yaml
ID: HA-INTEGRATION
Titel: Home Assistant Custom Integration für Kamerplanter
Kategorie: Integration & Smart Home
Fokus: Beides (Zierpflanze & Nutzpflanze)
Technologie: Python 3.12+, Home Assistant Core 2024.1+, HACS
Status: Entwurf
Version: 1.1
Autor: Business Analyst - Agrotech
Datum: 2026-02-27
Tags: [home-assistant, hacs, custom-integration, smart-home, iot, mqtt, polling]
Abhängigkeiten: [REQ-003, REQ-005, REQ-006, REQ-007, REQ-010, REQ-014, REQ-015, REQ-018, REQ-022, REQ-023, REQ-027, NFR-001]
```

<!-- Quelle: Smart-Home-HA-Integration Review HA-001 bis HA-008 -->

## 1. Scope & Abgrenzung

### 1.1 Was diese Spezifikation beschreibt

Die **Home Assistant Custom Integration** (`kamerplanter-ha`) ist ein **separates Repository** und wird über HACS installiert. Sie ist NICHT Teil des Kamerplanter-Backends.

| Aspekt | Beschreibung |
|--------|-------------|
| **Repository** | `kamerplanter-ha` (eigenständiges GitHub-Repo) |
| **Installation** | HACS (Home Assistant Community Store) oder manuelle Installation |
| **Runtime** | Home Assistant Core (Python-Addon) |
| **Kommunikation** | REST API Polling gegen Kamerplanter-Backend |
| **Auth** | API-Key (`kp_`-Prefix, REQ-023 §3.7) oder Light-Modus (REQ-027, ohne Auth) |

### 1.2 Abhängigkeiten von Kamerplanter

Die Custom Integration setzt voraus, dass das Kamerplanter-Backend folgende Funktionalitäten bereitstellt:

| Finding | Beschreibung | Kamerplanter-Referenz |
|---------|-------------|----------------------|
| A-001 | Stabile REST API mit Versionierungsgarantie | NFR-001 §4.2 (API-Stabilität für M2M-Consumer) |
| A-003 | API-Key-Authentifizierung für M2M-Zugriff | REQ-023 §3.7 (M2M-Authentifizierung) |
| A-006 | Konsistente JSON-Antwortformate | NFR-003 §2.4 (API-Response-Konsistenz) |
| A-007 | OpenAPI-Schema als versioniertes Artefakt | NFR-005 §2.4 (OpenAPI-Schema-Versionierung) |
| A-008 | iCal-Feed für Calendar-Entity | REQ-015 §4.2 (HA Calendar-Entity) |

---

## 2. Architektur

### 2.1 Verzeichnisstruktur

```
custom_components/kamerplanter/
├── __init__.py              # Setup, Config Entry, Platform-Registrierung
├── manifest.json            # HACS-Manifest (Version, Abhängigkeiten, IoT-Klasse)
├── config_flow.py           # UI: URL → Auth → Tenant → Entity-Auswahl
├── coordinator.py           # DataUpdateCoordinator (REST API Polling)
├── sensor.py                # Sensor-Entities (Phase, VPD-Target, EC-Target, ...)
├── binary_sensor.py         # Binary-Sensor-Entities (needs_attention, sensor_offline)
├── calendar.py              # Calendar-Entity (via iCal-Feed)
├── todo.py                  # Todo-Entity (fällige Tasks)
├── diagnostics.py           # Debug-Informationen (Config-Entry-Diagnostics)
├── const.py                 # Konstanten, Default Polling-Intervalle
├── icon.png                 # Kami-Maskottchen Icon 256×256 (Integrations-Menü)
├── icon@2x.png              # Kami-Maskottchen Icon 512×512 (HiDPI)
├── strings.json             # Lokalisierung (DE/EN)
└── translations/
    ├── de.json
    └── en.json
```

> **Icon-Assets:** Das Kami-Maskottchen (Happy-Pose) dient als Integration-Icon. Fertige Icons mit transparentem Hintergrund: `docs/img/ha_integration/icon.png` (256×256) und `docs/img/ha_integration/icon@2x.png` (512×512). Generierungs-Prompts: `spec/design/ha-integration-icon-kami.md`.
>
> ![Kami HA Icon](../../docs/img/ha_integration/icon.png)

### 2.2 manifest.json

```json
{
  "domain": "kamerplanter",
  "name": "Kamerplanter",
  "codeowners": ["@kamerplanter"],
  "config_flow": true,
  "documentation": "https://github.com/kamerplanter/kamerplanter-ha",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/kamerplanter/kamerplanter-ha/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

> **Hinweis:** `iot_class: cloud_polling` da die Integration per REST API pollt. Bei zukünftiger MQTT-Event-Unterstützung wird auf `local_push` oder `cloud_push` umgestellt.

---

## 3. Anforderungen (HA-001 bis HA-008)

### HA-001: Config Flow (URL + API-Key + Tenant)

**Beschreibung:** Standard-Konfigurationsassistent für die Ersteinrichtung der Integration in Home Assistant.

**Config Flow Steps:**

```
Step 1: Kamerplanter-URL eingeben
         Eingabe: http://raspberry:8000 oder https://kamerplanter.example.com
         Validierung: GET /api/health → {"status": "healthy", ...}
         Fehler: "Kamerplanter nicht erreichbar" bei Connection Error / non-200

Step 2: Authentifizierung konfigurieren
         Option A — Light-Modus (REQ-027): Kein Auth nötig → Skip
         Option B — API-Key: kp_... eingeben (REQ-023 §3.7)
         Option C — Fallback: Username/Password → POST /api/v1/auth/login → JWT
         Validierung: GET /api/v1/users/me → 200 OK

Step 3: Tenant auswählen (nur im Full-Modus)
         API-Call: GET /api/v1/users/me/tenants
         Dropdown: Liste aller Tenants des Users
         Default: Erster Tenant (bei Einzelnutzer nur einer)

Step 4: Entities konfigurieren
         Checkboxen: Welche Pflanzen/Locations/Tanks als Entities?
         Default: Alle verfügbaren Entities
         Option: "Alle auswählen" / "Keine auswählen"
```

### HA-002: Device Registry

**Beschreibung:** Eine Kamerplanter-Instanz = ein Device in Home Assistant.

| Aspekt | Wert |
|--------|------|
| **Device-Name** | Kamerplanter (`{tenant_name}` bei Multi-Tenant) |
| **Manufacturer** | Kamerplanter |
| **Model** | Kamerplanter Server |
| **SW Version** | Aus `GET /api/health → version` |
| **Identifiers** | `(kamerplanter, {url}_{tenant_slug})` |

Pflanzen, Locations und Tanks werden als **Entity-Gruppen** unter dem Device organisiert (nicht als Sub-Devices).

### HA-003: Entity Registry

**Beschreibung:** Dynamische Entity-Erstellung basierend auf Kamerplanter-API-Antworten. Entity-IDs werden aus dem stabilen ArangoDB `_key` abgeleitet.

**Entity-Mapping-Tabelle:**

| HA-Entity-ID-Pattern | Kamerplanter-Quelle | HA-Entity-Typ | Einheit |
|----------------------|---------------------|---------------|---------|
| `sensor.kp_{plant}_phase` | `current_phase` | `sensor` | — |
| `sensor.kp_{plant}_days_in_phase` | `phase_histories.entered_at` (berechnet) | `sensor` | `d` |
| `sensor.kp_{plant}_vpd_target` | `requirement_profiles.vpd_target_kpa` | `sensor` | `kPa` |
| `sensor.kp_{plant}_ec_target` | `nutrient_profiles.target_ec_ms` | `sensor` | `mS/cm` |
| `sensor.kp_{plant}_photoperiod` | `requirement_profiles.photoperiod_hours` | `sensor` | `h` |
| `sensor.kp_{plant}_gdd_accumulated` | GDD-Tracking (berechnet) | `sensor` | `°Cd` |
| `sensor.kp_{plant}_harvest_readiness` | `GET /harvest/readiness/{id}` | `sensor` | `%` |
| `sensor.kp_{plant}_karenz_remaining` | Karenz-Gate (berechnet) | `sensor` | `d` |
| `sensor.kp_{plant}_next_watering` | `GET /care-reminders/` | `sensor` | — |
| `sensor.kp_{plant}_health_score` | IPM + Quality (aggregiert) | `sensor` | `%` |
| `sensor.kp_{plant}_active_channels` | `GET /plant-instances/{key}/active-channels` | `sensor` | — |
| `sensor.kp_{plant}_{channel_slug}_mix` | `_current_dosages.channels[]` (Coordinator) | `sensor` | — |
| `binary_sensor.kp_{plant}_needs_attention` | Alerts + überfällige Tasks | `binary_sensor` | — |
| `sensor.kp_{location}_active_plants` | Slot-Belegung | `sensor` | — |
| `sensor.kp_{tank}_ec` | `TankState.ec_ms` | `sensor` | `mS/cm` |
| `sensor.kp_{tank}_ph` | `TankState.ph` | `sensor` | `pH` |
| `sensor.kp_{tank}_fill_level` | `TankState.fill_level_percent` | `sensor` | `%` |
| `sensor.kp_{tank}_water_temp` | `TankState.water_temp_celsius` | `sensor` | `°C` |
| `sensor.kp_{tank}_dissolved_oxygen` | `TankState.dissolved_oxygen_mgl` | `sensor` | `mg/L` |
| `sensor.kp_{tank}_orp` | `TankState.orp_mv` | `sensor` | `mV` |
| `sensor.kp_{tank}_solution_age_days` | Berechnet aus letztem `full_change` TankFillEvent (Q10-korrigiert) | `sensor` | `d` |
| `binary_sensor.kp_{tank}_alert_active` | `check_alerts()` Result (aggregiert) | `binary_sensor` | — |
| `calendar.kp_tasks` | CalendarFeed (iCal) | `calendar` | — |
| `todo.kp_{location}_tasks` | `GET /tasks/?status=pending` | `todo` | — |
| `sensor.kp_{actuator}_state` | `Actuator.current_state` | `sensor` | — |
| `binary_sensor.kp_sensor_offline` | SensorHealth | `binary_sensor` | — |
| `sensor.kp_{location}_vpd_current` | Berechneter VPD | `sensor` | `kPa` |

**Entity-ID-Generierung:**

```python
# Entity-ID aus ArangoDB _key ableiten
# _key: "plant_northern_lights_3" → entity_id: "sensor.kp_northern_lights_3_phase"
def entity_id(prefix: str, key: str, suffix: str) -> str:
    slug = key.replace("-", "_").lower()
    return f"{prefix}.kp_{slug}_{suffix}"
```

### HA-004: Coordinator mit konfigurierbarem Polling-Intervall

**Beschreibung:** Mehrere DataUpdateCoordinators mit unterschiedlichen Polling-Intervallen je nach Datentyp.

| Coordinator | Polling-Intervall | API-Endpoint | Entities |
|-------------|-------------------|-------------|----------|
| `PlantCoordinator` | 300s (5 min) | `GET /api/v1/t/{slug}/plants/` | Phase, Days in Phase, VPD Target, EC Target, Health Score, Karenz, Harvest Readiness |
| `LocationCoordinator` | 300s (5 min) | `GET /api/v1/t/{slug}/locations/` | Active Plants, Capacity, VPD Current |
| `TankCoordinator` | 120s (2 min) | `GET /api/v1/t/{slug}/tanks/` + `GET /tanks/{id}/states/latest` | EC, pH, Fill Level, Water Temp |
| `AlertCoordinator` | 60s (1 min) | `GET /api/v1/t/{slug}/alerts/?active=true` | Needs Attention, Sensor Offline |
| `TaskCoordinator` | 300s (5 min) | `GET /api/v1/t/{slug}/tasks/?status=pending` | Todo Items |

**Konfigurierbar:** Polling-Intervalle können in den Integrations-Optionen angepasst werden (Minimum: 30s für Alerts, 60s für Tanks, 120s für Plants/Locations/Tasks).

**Fehlerbehandlung:**

```python
class KamerplanterCoordinator(DataUpdateCoordinator):
    async def _async_update_data(self):
        try:
            data = await self.api.fetch_plants()
            return data
        except ConnectionError:
            raise UpdateFailed("Kamerplanter nicht erreichbar")
        except AuthenticationError:
            raise ConfigEntryAuthFailed("API-Key ungültig oder revoked")
```

> **Zukünftiges Upgrade:** Bei Implementierung eines MQTT-Event-Bus im Kamerplanter-Backend können Alert- und Phase-Transition-Events per Push empfangen werden. Der `AlertCoordinator` wird dann durch einen MQTT-Listener ersetzt.

### HA-005: HACS-Repository-Struktur

**Beschreibung:** Standardkonformes HACS-Repository für einfache Installation.

**Repository-Struktur:**

```
kamerplanter-ha/
├── custom_components/
│   └── kamerplanter/
│       ├── (siehe §2.1 Verzeichnisstruktur)
│       └── ...
├── hacs.json
├── README.md
├── LICENSE
└── .github/
    └── workflows/
        ├── validate.yml       # HACS-Validation Action
        └── release.yml        # Semantic Versioning
```

**hacs.json:**

```json
{
  "name": "Kamerplanter",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```

### HA-006: Calendar-Entity via iCal-Feed

**Beschreibung:** Nutzt den REQ-015 CalendarFeed-Endpoint direkt für eine native HA Calendar-Entity.

**Implementierung:**

```python
# calendar.py
class KamerplanterCalendar(CalendarEntity):
    """Kamerplanter Calendar Entity via iCal-Feed."""

    def __init__(self, coordinator, feed_id, feed_token):
        self._feed_id = feed_id
        self._feed_token = feed_token

    @property
    def event(self) -> CalendarEvent | None:
        """Nächstes anstehendes Event."""
        # Parsed aus iCal-Feed (VEVENT mit frühestem DTSTART in der Zukunft)
        ...

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Events im Zeitraum."""
        # GET /api/v1/calendar/feeds/{feed_id}/feed.ics?token={token}
        # Parse iCal → CalendarEvent-Liste
        ...
```

**Kamerplanter-Endpoint:** `GET /api/v1/calendar/feeds/{feed_id}/feed.ics?token={token}` (Token-basiert, kein JWT nötig — siehe REQ-015 §4.2)

### HA-007: Todo-Entity für fällige Tasks

**Beschreibung:** Mapped REQ-006 Tasks auf native HA Todo-Items.

**Implementierung:**

```python
# todo.py
class KamerplanterTodoList(TodoListEntity):
    """Kamerplanter fällige Tasks als Todo-Liste."""

    @property
    def todo_items(self) -> list[TodoItem]:
        """Aktuelle Todo-Items aus TaskCoordinator."""
        return [
            TodoItem(
                uid=task["_key"],
                summary=task["title"],
                due=task.get("due_date"),
                status=TodoItemStatus.NEEDS_ACTION,
            )
            for task in self.coordinator.data
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Optional: Task in Kamerplanter erstellen."""
        # POST /api/v1/t/{slug}/tasks/
        ...

    async def async_update_todo_item(self, uid: str, item: TodoItem) -> None:
        """Task als erledigt markieren."""
        # PATCH /api/v1/t/{slug}/tasks/{uid} → {"status": "completed"}
        ...
```

### HA-008: Diagnostics (Debug-Info)

**Beschreibung:** Config-Entry-Diagnostics für Debugging und Support.

**Implementierung:**

```python
# diagnostics.py
async def async_get_config_entry_diagnostics(hass, config_entry):
    """Diagnostics für Kamerplanter-Integration."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "kamerplanter_version": coordinator.server_version,
        "kamerplanter_mode": coordinator.server_mode,  # "full" oder "light"
        "tenant_slug": config_entry.data.get("tenant_slug"),
        "plant_count": len(coordinator.plants),
        "location_count": len(coordinator.locations),
        "tank_count": len(coordinator.tanks),
        "active_alerts": len(coordinator.alerts),
        "pending_tasks": len(coordinator.tasks),
        "coordinator_update_intervals": {
            "plants": coordinator.plant_interval.total_seconds(),
            "tanks": coordinator.tank_interval.total_seconds(),
            "alerts": coordinator.alert_interval.total_seconds(),
        },
        "last_successful_update": coordinator.last_update_success.isoformat(),
        "api_key_prefix": config_entry.data.get("api_key", "")[:8] + "...",
    }
```

---

## 4. HA-Automation-Blueprints

Die folgenden Blueprints zeigen typische Automationen, die auf den Kamerplanter-Entities aufbauen.

### Blueprint 1: Phasenwechsel → Lichtprogramm ändern

```yaml
# Trigger: sensor.kp_{plant}_phase wechselt zu "flowering"
alias: "KP: Blüte-Start → 12/12 Licht"
description: "Lichtprogramm auf 12h/12h umstellen wenn Kamerplanter Blüte meldet"
trigger:
  - platform: state
    entity_id: sensor.kp_northern_lights_phase
    to: "flowering"
condition: []
action:
  - service: automation.turn_off
    target:
      entity_id: automation.licht_18_6_veg
  - service: automation.turn_on
    target:
      entity_id: automation.licht_12_12_bloom
  - service: notify.mobile_app_phone
    data:
      title: "Kamerplanter: Blüte gestartet"
      message: "Northern Lights wechselt in Blüte. Licht auf 12/12 umgestellt."
mode: single
```

### Blueprint 2: VPD-Sollwert → Befeuchter-Steuerung

```yaml
# Modus B: KP liefert Sollwert, HA regelt Befeuchter
alias: "KP: VPD-Regelung mit KP-Sollwert"
description: "Befeuchter ein/aus basierend auf Kamerplanter VPD-Ziel"
trigger:
  - platform: template
    value_template: >
      {{ states('sensor.growzelt_vpd') | float(0) >
         (states('sensor.kp_northern_lights_vpd_target') | float(1.0) + 0.2) }}
    id: vpd_too_high
  - platform: template
    value_template: >
      {{ states('sensor.growzelt_vpd') | float(0) <
         (states('sensor.kp_northern_lights_vpd_target') | float(1.0) - 0.1) }}
    id: vpd_ok
condition: []
action:
  - choose:
      - conditions:
          - condition: trigger
            id: vpd_too_high
        sequence:
          - service: switch.turn_on
            target:
              entity_id: switch.befeuchter_zelt_1
      - conditions:
          - condition: trigger
            id: vpd_ok
        sequence:
          - service: switch.turn_off
            target:
              entity_id: switch.befeuchter_zelt_1
mode: single
```

### Blueprint 3: Erntebereitschaft → Push-Benachrichtigung

```yaml
# Trigger: Erntebereitschaft > 80% UND Karenz abgelaufen
alias: "KP: Ernte bald bereit"
description: "Benachrichtigung wenn Erntebereitschaft 80% erreicht"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_white_widow_harvest_readiness
    above: 80
condition:
  - condition: template
    value_template: >
      {{ states('sensor.kp_white_widow_karenz_remaining') | int(99) == 0 }}
action:
  - service: notify.mobile_app_phone
    data:
      title: "Ernte bereit!"
      message: >
        White Widow Readiness: {{ states('sensor.kp_white_widow_harvest_readiness') }}%.
        Karenz abgelaufen. Trichome pruefen!
  - service: persistent_notification.create
    data:
      title: "Kamerplanter: Ernte bereit"
      message: "White Widow ist erntereif. Readiness Score: {{ states('sensor.kp_white_widow_harvest_readiness') }}%"
mode: single
```

### Blueprint 4: Frostwarnung → Gewächshaus-Heizung

```yaml
# Nutzt KP Wetter-Integration (REQ-005) oder direkte HA-Wetter-Integration
alias: "KP: Frostwarnung → Heizung ein"
description: "Gewächshaus-Heizung einschalten bei KP-Frostwarnung"
trigger:
  - platform: state
    entity_id: binary_sensor.kp_gewaechshaus_frost_warning
    to: "on"
condition:
  - condition: state
    entity_id: switch.gewaechshaus_heizung
    state: "off"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.gewaechshaus_heizung
  - service: climate.set_temperature
    target:
      entity_id: climate.gewaechshaus
    data:
      temperature: 5
  - service: notify.mobile_app_phone
    data:
      title: "Frostwarnung!"
      message: >
        Kamerplanter meldet Frost fuer {{ state_attr('binary_sensor.kp_gewaechshaus_frost_warning', 'location') }}.
        Heizung eingeschaltet (Frostschutz 5 Grad C).
mode: single
```

### Blueprint 5: Tank niedrig → Auffüll-Erinnerung

```yaml
# Trigger: Tank-Füllstand unter 20%
alias: "KP: Tank fast leer"
description: "Warnung wenn Tank unter 20% Fuellstand"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_haupttank_zelt1_fill_level
    below: 20
condition:
  - condition: template
    value_template: >
      {{ (as_timestamp(now()) - as_timestamp(
          states.sensor.kp_haupttank_zelt1_fill_level.last_changed)) > 3600 }}
action:
  - service: notify.mobile_app_phone
    data:
      title: "Tank fast leer!"
      message: >
        Haupttank Zelt 1: {{ states('sensor.kp_haupttank_zelt1_fill_level') }}% Restfuellstand.
        EC: {{ states('sensor.kp_haupttank_zelt1_ec') }} mS/cm,
        pH: {{ states('sensor.kp_haupttank_zelt1_ph') }}.
        Bitte auffuellen!
mode: single
```

### Blueprint 6: Alle Ausbringkanaele einer Pflanze giessen

```yaml
# Trigger: Taeglich um 8:00 Uhr alle aktiven Kanaele der Pflanze giessen
alias: "KP: Morgendliches Giessen aller Kanaele"
description: "Iteriert ueber alle aktiven Ausbringkanaele und fuehrt Giessvorgang aus"
trigger:
  - platform: time
    at: "08:00:00"
condition:
  - condition: numeric_state
    entity_id: sensor.kp_149369_active_channels
    above: 0
action:
  - repeat:
      for_each: >
        {{ state_attr('sensor.kp_149369_active_channels', 'channel_ids') }}
      sequence:
        - service: kamerplanter.water_channel
          data:
            plant_key: "149369"
            channel_id: "{{ repeat.item }}"
            volume_liters: 0.7
            notes: "Automatisches Morgengiessen via HA"
mode: single
```

### Blueprint 7: Gezieltes Giessen eines einzelnen Kanals

```yaml
# Manueller Trigger: Einen bestimmten Kanal einer Pflanze giessen
alias: "KP: Giesskanne 10L befuellen und giessen"
description: "Giesst den Giesskanne-10L-Kanal mit Dosierungen aus dem Naehrstoffplan"
trigger:
  - platform: event
    event_type: call_service
    event_data:
      domain: script
      service: kp_giessen_giesskanne
action:
  - service: kamerplanter.water_channel
    data:
      entity_id: sensor.kp_149369_giesskanne_10l_mix
      volume_liters: 0.7
      measured_ec_ms: "{{ states('sensor.ec_meter_growroom') | float(0) }}"
      measured_ph: "{{ states('sensor.ph_meter_growroom') | float(0) }}"
      notes: "Gegossen mit gemessenen EC/pH-Werten"
mode: single
```

### Sensor: Active Channels (Ausbringkanaele)

Jede aktive Pflanzeninstanz erhaelt einen `active_channels`-Sensor, der alle aktuell aktiven Ausbringkanaele aus dem zugewiesenen Naehrstoffplan auflistet.

**Entity-ID:** `sensor.kp_{plant_key}_active_channels`

**State:** Anzahl aktiver Kanaele (z.B. `2`)

**Attribute:**

| Attribut | Typ | Beschreibung |
|----------|-----|-------------|
| `plant_key` | `str` | ArangoDB-Key der Pflanzeninstanz |
| `channel_ids` | `list[str]` | Liste aller aktiven `channel_id`-Werte |
| `{channel_id}` | `dict` | Pro Kanal: `label`, `application_method`, `target_ec_ms`, `target_ph`, `phase_name`, `week_start`, `week_end`, `dosages` (dict Produktname → ml/L) |

**Beispiel-Attribute:**

```yaml
plant_key: "149369"
channel_ids:
  - "giesskanne_10l"
  - "blattpflege"
giesskanne_10l:
  label: "Giesskanne 10L"
  application_method: "drench"
  target_ec_ms: 1.4
  target_ph: 6.2
  phase_name: "vegetative"
  week_start: 3
  week_end: 7
  dosages:
    Plagron Terra Grow: 0.5
    Plagron Power Roots: 0.25
blattpflege:
  label: "Blattpflege Sprueher"
  application_method: "foliar"
  target_ec_ms: null
  target_ph: null
  phase_name: "vegetative"
  week_start: 3
  week_end: 7
  dosages:
    Plagron Pure Zym: 0.1
```

**Datenquelle:** `GET /api/v1/t/{slug}/plant-instances/{key}/active-channels?current_week=N` (neuer Backend-Endpoint). Der Plant-Coordinator berechnet `current_week` aus `current_phase_started_at` und ruft den Endpoint bei jedem Poll-Zyklus (300s) ab.

### Sensor: Channel Mix (Dosierungen pro Kanal)

Pro aktivem Ausbringkanal wird ein separater `{channel_slug}_mix`-Sensor erstellt, der die einzelnen Duengemittel-Dosierungen als Attribute exponiert.

**Entity-ID:** `sensor.kp_{plant_key}_{channel_slug}_mix`

**State:** Anzahl Duengemittel im Kanal (z.B. `3`)

**Attribute:**

| Attribut | Typ | Beschreibung |
|----------|-----|-------------|
| `plant_key` | `str` | ArangoDB-Key der Pflanzeninstanz |
| `channel_id` | `str` | ID des Ausbringkanals |
| `{Produktname} (ml/L)` | `float` | Dosierung pro Produkt in ml pro Liter |

**Beispiel-Attribute:**

```yaml
plant_key: "149369"
channel_id: "giesskanne_10l"
Plagron Terra Grow (ml/L): 0.5
Plagron Power Roots (ml/L): 0.25
Plagron Pure Zym (ml/L): 0.1
```

### Service: water_channel (Ausbringkanal giessen)

Fuehrt eine Bewaesserung fuer einen bestimmten Ausbringkanal einer Pflanzeninstanz durch. Erstellt einen Watering-Log-Eintrag im Kamerplanter-Backend mit den aktuellen Dosierungen aus dem Naehrstoffplan.

**Service-Name:** `kamerplanter.water_channel`

**Felder:**

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|-------------|
| `entity_id` | `entity` | Nein | Channel-Entity (z.B. `sensor.kp_149369_giesskanne_10l_mix`). Plant/Channel werden automatisch aufgeloest. |
| `plant_key` | `str` | Nein | Direkter ArangoDB-Key der Pflanzeninstanz. Nur wenn keine `entity_id`. |
| `channel_id` | `str` | Nein | ID des Ausbringkanals. Nur zusammen mit `plant_key`. |
| `volume_liters` | `float` | Nein | Gegossenes Volumen (L). Default: Kanalvolumen aus Plan. |
| `application_method` | `select` | Nein | `drench` (default), `foliar`, `fertigation`, `capillary` |
| `measured_ec_ms` | `float` | Nein | Gemessener EC-Wert (mS/cm) |
| `measured_ph` | `float` | Nein | Gemessener pH-Wert |
| `notes` | `str` | Nein | Optionale Bemerkungen |

**Aufloesung plant_key + channel_id (3 Strategien):**

1. **State-Attribute:** Liest `plant_key` und `channel_id` direkt aus den Attributen der Entity
2. **Entity-ID-Pattern:** Parst `sensor.kp_{plant_slug}_{channel_slug}_mix` und gleicht mit Coordinator-Daten ab
3. **Direkte Parameter:** `plant_key` + `channel_id` als Service-Felder

**Ablauf:**

```
1. Aufloesen: plant_key + channel_id (aus entity_id oder direkte Parameter)
2. Dosierungen laden: Plant-Coordinator → _current_dosages → channels[] → dosages[]
3. Volumen bestimmen: Parameter > Kanal-Volumen aus Plan
4. Watering-Log erstellen: POST /api/v1/watering-logs
5. Coordinators refreshen: Alle 5 Coordinators neu laden
```

**Backend-Endpoint:** `POST /api/v1/watering-logs` (nicht tenant-scoped)

**Payload-Beispiel:**

```json
{
  "application_method": "drench",
  "volume_liters": 0.7,
  "plant_keys": ["149369"],
  "channel_id": "giesskanne_10l",
  "fertilizers_used": [
    {"fertilizer_key": "plagron-terra-grow", "ml_per_liter": 0.5},
    {"fertilizer_key": "plagron-power-roots", "ml_per_liter": 0.25}
  ],
  "performed_by": "home_assistant"
}
```

### Service: fill_tank (Tank befuellen)

Erstellt ein Tank-Fill-Event mit automatischer Dosierungsaufloesung aus dem Naehrstoffplan der zugewiesenen Location.

**Service-Name:** `kamerplanter.fill_tank`

**Felder:**

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|-------------|
| `entity_id` | `entity` | Nein | Beliebige Tank-Entity (z.B. `sensor.kp_90639_info`) |
| `tank_key` | `str` | Nein | Direkter ArangoDB-Key (Legacy). Nur wenn keine `entity_id`. |
| `fill_type` | `select` | Nein | `full_change` (default), `top_up`, `adjustment` |
| `volume_liters` | `float` | Nein | Befuelltes Volumen (L). Default: Tank-Nennvolumen. |
| `measured_ec_ms` | `float` | Nein | Gemessener EC-Wert (mS/cm) nach Mischen |
| `measured_ph` | `float` | Nein | Gemessener pH-Wert nach Mischen |
| `notes` | `str` | Nein | Optionale Bemerkungen |

**Dosierungsaufloesung:** Sucht im Location-Coordinator den Primary Run, matched Delivery Channels zum Tank (via Name/Volumen im Label) und uebernimmt die Dosierungen.

### Backend-Endpoints: Active Channels

Zwei neue API-Endpoints liefern die aktiven Ausbringkanaele fuer Pflanzeninstanzen und Pflanzdurchlaeufe:

**`GET /api/v1/t/{slug}/plant-instances/{key}/active-channels?current_week=N`**

Gibt die aktiven Delivery Channels der aktuellen Phase einer Pflanzeninstanz zurueck. `current_week` ist pflicht.

**`GET /api/v1/t/{slug}/planting-runs/{key}/active-channels?current_week=N`**

Gibt die aktiven Delivery Channels der dominanten Phase eines Pflanzdurchlaufs zurueck. `current_week` ist optional — wird aus dem Startdatum berechnet wenn nicht angegeben.

**Response-Format (ActiveChannelResponse):**

```json
[
  {
    "channel_id": "giesskanne_10l",
    "label": "Giesskanne 10L",
    "application_method": "drench",
    "target_ec_ms": 1.4,
    "target_ph": 6.2,
    "plan_key": "abc123",
    "plan_name": "Tomate Plagron Terra",
    "entry_key": "def456",
    "phase_name": "vegetative",
    "week_start": 3,
    "week_end": 7,
    "dosages": [
      {
        "fertilizer_key": "plagron-terra-grow",
        "product_name": "Plagron Terra Grow",
        "ml_per_liter": 0.5,
        "optional": false,
        "mixing_priority": 10
      }
    ]
  }
]
```

---

## 5. Steuerungsmodi (Kamerplanter vs. HA)

Für Aktoren (REQ-018) muss klar definiert sein, wer die Steuerung übernimmt. Die Wahl ist **pro Location/Aktor konfigurierbar**:

| Modus | Beschreibung | Empfohlen für |
|-------|-------------|---------------|
| **Modus A: KP steuert direkt** | Kamerplanter ControlEngine steuert Aktoren via HA-Service-Calls. HA-Automationen für dieselben Aktoren werden deaktiviert. | Einsteiger, Nutzer ohne eigene HA-Automationen |
| **Modus B: KP liefert Sollwerte, HA regelt** | Kamerplanter publisht Sollwerte (VPD-Target, EC-Target, Photoperiode) als Sensor-Entities. HA-Automationen lesen die Sollwerte und regeln selbst. | HA-Power-User, Node-RED-Nutzer, Nutzer mit bestehenden Regelkreisen |

**Wichtig:** Beide Modi dürfen NICHT gleichzeitig für denselben Aktor aktiv sein — das führt zu Oszillation (zwei Regler kämpfen gegeneinander).

---

## 6. Non-Funktionale Anforderungen (HA-NFR)

<!-- Quelle: Abgeleitet aus vibe-coding/docs/home-assistant/integration/spec.md -->

Die folgenden NFRs definieren verbindliche Implementierungsmuster für die `kamerplanter-ha` Custom Integration. Sie stellen sicher, dass die Integration den etablierten HA-Architekturprinzipien folgt und sich identisch zu qualitativ hochwertigen Custom Integrations verhält.

### HA-NFR-001: Entity-Referenzierung via hass.data

**Problem:** Entity-IDs werden aus dem Entity-Namen abgeleitet, nicht aus der Config-Entry-ID. Bei ULIDs als Entry-ID schlägt die String-basierte Entity-ID-Konstruktion fehl.

**Anforderung:** Alle plattformübergreifenden Entity-Zugriffe MÜSSEN über direkte Python-Objekt-Referenzen in `hass.data` erfolgen. String-basierte Entity-ID-Konstruktion und Entity-Registry-Lookups sind verboten.

```python
# ✅ Korrekt: Entity-Objekte in hass.data registrieren
async def async_setup_entry(hass, entry, async_add_entities):
    entity = KamerplanterPhaseSensor(entry)
    store = hass.data.setdefault(DOMAIN, {}).setdefault('_entities', {})
    store[entry.entry_id] = {ENTITY_KEY_PHASE: entity}
    async_add_entities([entity])

# ✅ Korrekt: Zugriff via Dict-Lookup (O(1), typsicher)
entity = hass.data[DOMAIN]['_entities'][entry.entry_id][ENTITY_KEY_PHASE]

# ❌ Verboten: Entity-ID aus Entry-ID ableiten
entity_id = f"sensor.kamerplanter_{entry.entry_id}_phase"
```

**Setup-Reihenfolge:** Die Plattform, die Entities in `hass.data` ablegt, MUSS in der `PLATFORMS`-Liste vor Plattformen stehen, die darauf zugreifen. Alternativ: Zugriff erst nach `async_forward_entry_setups`.

---

### HA-NFR-002: Service-Registrierung mit Idempotenz-Guard

**Problem:** `async_setup_entry` wird bei mehreren Config-Entries mehrfach aufgerufen. Ohne Guard werden Services doppelt registriert.

**Anforderung:** Services MÜSSEN einmalig pro HA-Start registriert werden. Vor jeder Registrierung MUSS ein `has_service`-Guard prüfen, ob der Service bereits existiert. Services MÜSSEN `entry_id` als optionalen Filter akzeptieren, um bei Multi-Instance-Setups gezielt eine Instanz anzusprechen.

```python
# ✅ Korrekt: Idempotenz-Guard
async def async_setup_entry(hass, entry):
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        await _async_register_services(hass)

async def _async_register_services(hass):
    async def handle_refresh(call: ServiceCall) -> None:
        target_id = call.data.get('entry_id', '')
        entries = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if not target_id or e.entry_id == target_id
        ]
        for entry in entries:
            coordinator = hass.data[DOMAIN][entry.entry_id]
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
```

**services.yaml:** Jeder registrierte Service MUSS eine `services.yaml`-Beschreibung mit `name`, `description` und `fields` haben, damit er in den HA-Entwicklerwerkzeugen (Aktionen) sichtbar und dokumentiert ist.

**Kamerplanter-Services:**

| Service | Beschreibung |
|---------|-------------|
| `kamerplanter.refresh_data` | Sofortiges Re-Polling aller Coordinators (oder eines bestimmten via `entry_id`) |
| `kamerplanter.clear_cache` | Lokalen Storage-Cache leeren und Daten neu laden |
| `kamerplanter.fill_tank` | Tank-Befuellung mit automatischer Dosierungsaufloesung aus Naehrstoffplan |
| `kamerplanter.water_channel` | Bewaesserung eines Ausbringkanals einer Pflanzeninstanz (erstellt Watering-Log) |

---

### HA-NFR-003: Sofortige Zustandspropagierung

**Problem:** Der Coordinator-Polling-Zyklus (60s–300s) ist für Reaktionen auf User-Aktionen zu langsam. Nach einem Button-Press oder Service-Call muss die UI sofort aktualisiert werden.

**Anforderung:** Entity-Werte, die als direkte Reaktion auf eine Benutzeraktion geändert werden, MÜSSEN sofort via `async_write_ha_state()` propagiert werden — ohne auf den nächsten Coordinator-Zyklus zu warten.

```python
# ✅ Korrekt: Sofortige UI-Aktualisierung nach Service-Call
class KamerplanterTodoList(TodoListEntity):
    async def async_update_todo_item(self, uid: str, item: TodoItem) -> None:
        await self.api.complete_task(uid)  # API-Call an Kamerplanter
        # Sofort lokal aktualisieren, nicht auf nächsten Poll warten
        self._items = [i for i in self._items if i.uid != uid]
        self.async_write_ha_state()  # ← UI sieht Änderung sofort
```

**Abgrenzung:** Reguläre Daten-Updates (Plant-Phase, Tank-EC) werden weiterhin über den Coordinator gepollt. `async_write_ha_state()` wird nur für User-initiierte Aktionen verwendet.

---

### HA-NFR-004: Datenpersistenz und Schema-Versionierung

**Problem:** Entity-Zustände und strukturierte Daten müssen HA-Neustarts überleben. Ohne Versionierung brechen Schema-Änderungen bei Updates bestehende Installationen.

**Anforderung:**

| Datentyp | Persistenz-Mechanismus | Verwendung in kamerplanter-ha |
|----------|----------------------|-------------------------------|
| Einzelne Entity-States | `RestoreEntity` | Letzter bekannter Phase-Wert, Tank-Werte bei HA-Neustart |
| Strukturierte Daten | `helpers.storage.Store` | Coordinator-Cache, Konfigurationsdaten |

**RestoreEntity — Pflicht für alle Sensor-Entities:**

```python
class KamerplanterPhaseSensor(RestoreEntity, SensorEntity):
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ('unknown', 'unavailable', ''):
            self._attr_native_value = last.state
        self.async_write_ha_state()
```

**helpers.storage — Schema-Versionierung:**

```python
STORAGE_VERSION = 1  # Bei Schema-Änderung inkrementieren + Migrationspfad

class KamerplanterStorage:
    def __init__(self, hass, entry):
        self._store = storage.Store(
            hass, STORAGE_VERSION,
            f"{DOMAIN}_data_{entry.entry_id}",
        )
```

**Regel:** `STORAGE_VERSION` MUSS bei jeder strukturellen Änderung des gespeicherten Schemas inkrementiert werden. Migrationscode für Version N-1 → N MUSS mitgeliefert werden.

---

### HA-NFR-005: Plattform-Entkopplung via Event-Bus

**Problem:** Direkte Imports zwischen Plattformen (`sensor.py` importiert `calendar.py`) erzeugen enge Kopplung und zirkuläre Abhängigkeiten.

**Anforderung:** Plattformübergreifende Kommunikation MUSS über den HA Event-Bus erfolgen. Direkte Cross-Plattform-Imports sind verboten (Ausnahme: gemeinsame Konstanten aus `const.py`).

```python
# const.py — Gemeinsame Event-Typen
EVENT_TASK_COMPLETED = f"{DOMAIN}_task_completed"
EVENT_DATA_REFRESHED = f"{DOMAIN}_data_refreshed"
```

```python
# todo.py — Event senden nach Task-Completion
async def async_update_todo_item(self, uid, item):
    await self.api.complete_task(uid)
    self.hass.bus.fire(EVENT_TASK_COMPLETED, {
        'entry_id': self._entry.entry_id,
        'task_key': uid,
    })
```

```python
# calendar.py — Event empfangen → Kalender aktualisieren
async def async_added_to_hass(self) -> None:
    self._unsub = self.hass.bus.async_listen(
        EVENT_TASK_COMPLETED, self._on_task_completed)

async def async_will_remove_from_hass(self) -> None:
    if self._unsub:
        self._unsub()  # ← PFLICHT: Listener abmelden

async def _on_task_completed(self, event: Event) -> None:
    if event.data.get('entry_id') != self._entry.entry_id:
        return
    await self.coordinator.async_request_refresh()
```

**Speicherleck-Prävention:** Event-Listener MÜSSEN in `async_will_remove_from_hass()` abgemeldet werden. Fehlende Abmeldung führt zu Speicherlecks nach Integration-Reload.

---

### HA-NFR-006: Laufzeit-Konfiguration und Reload

**Problem:** Optionsänderungen im Config-Flow (z.B. Polling-Intervall, Tenant-Wechsel) werden erst nach HA-Neustart wirksam — inakzeptabel für Nutzer.

**Anforderung:** Konfigurationsänderungen MÜSSEN sofort wirksam werden. Die Integration MUSS `add_update_listener` mit `async_on_unload` registrieren.

```python
async def async_setup_entry(hass, entry):
    coordinator = KamerplanterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(
        entry.add_update_listener(_async_reload_entry)
    )
    return True

async def _async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
```

**Konfigurierbare Optionen (Options-Flow):**

| Option | Default | Beschreibung |
|--------|---------|-------------|
| Polling-Intervall Plants | 300s | Aktualisierungsrate für Pflanzen-Entities |
| Polling-Intervall Tanks | 120s | Aktualisierungsrate für Tank-Entities |
| Polling-Intervall Alerts | 60s | Aktualisierungsrate für Alert-Entities |
| Entity-Auswahl | Alle | Welche Pflanzen/Locations/Tanks als Entities |

**Selektiver Reload:** Bei Änderung des Polling-Intervalls wird nur `coordinator.update_interval` aktualisiert + `async_request_refresh()` statt vollständiger Reload.

---

### HA-NFR-007: Button-Entities für serverseitige Aktionen

**Problem:** Lovelace-Buttons können keine Jinja-Templates in `service_data` auswerten. Aktionen mit berechneten Werten (Zeitstempel, dynamische Parameter) schlagen fehl.

**Anforderung:** Aktionen die serverseitig berechnete Werte benötigen MÜSSEN als `ButtonEntity` implementiert werden. Die gesamte Logik läuft in Python — kein Jinja, kein Template-Rendering.

**Kamerplanter Button-Entities:**

| Button | Icon | Aktion |
|--------|------|--------|
| `button.kp_refresh_all` | `mdi:refresh` | Sofortiges Re-Polling aller Coordinators |
| `button.kp_{location}_refresh` | `mdi:refresh` | Re-Polling für einen bestimmten Standort |

```python
class KamerplanterRefreshButton(ButtonEntity):
    _attr_name = "Daten aktualisieren"
    _attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        coordinator = self.hass.data[DOMAIN][self._entry.entry_id]
        await coordinator.async_request_refresh()
        # Event feuern für andere Plattformen (HA-NFR-005)
        self.hass.bus.fire(EVENT_DATA_REFRESHED, {
            'entry_id': self._entry.entry_id,
            'timestamp': datetime.now(tz=timezone.utc).isoformat(),
        })
```

---

### Zusammenfassung HA-NFRs

| NFR | Kernregel | Verboten |
|-----|-----------|----------|
| HA-NFR-001 | Entity-Referenzen via `hass.data` Dict-Lookup | String-basierte Entity-ID-Konstruktion |
| HA-NFR-002 | `has_service`-Guard + `entry_id`-Filter | Doppelte Service-Registrierung |
| HA-NFR-003 | `async_write_ha_state()` bei User-Aktionen | Warten auf Coordinator-Zyklus nach User-Interaktion |
| HA-NFR-004 | `RestoreEntity` + `helpers.storage` mit Versionierung | Schema-Änderungen ohne STORAGE_VERSION-Inkrement |
| HA-NFR-005 | Event-Bus für Cross-Plattform-Kommunikation | Direkte Imports zwischen `sensor.py`/`calendar.py`/`todo.py` |
| HA-NFR-006 | `add_update_listener` + `async_on_unload` | Optionsänderungen erst nach HA-Neustart wirksam |
| HA-NFR-007 | `ButtonEntity` für serverseitige Aktionen | Jinja-Templates in Lovelace `service_data` |

---

## 7. Optionalitäts-Checkliste

Die HA Custom Integration ist vollständig **optional**. Kamerplanter funktioniert ohne Home Assistant:

| Feature | Ohne HA nutzbar? | Kommentar |
|---------|-----------------|-----------|
| Phasensteuerung (REQ-003) | Ja | Phasenwechsel manuell oder zeitbasiert |
| Dünge-Logik (REQ-004) | Ja | Mischrezept-Berechnung reine Logik |
| Sensor-Monitoring (REQ-005) | Ja | Manuelle Eingabe als Fallback |
| Aktor-Steuerung (REQ-018) | Eingeschränkt | `protocol: manual` → Tasks statt Befehle |
| Aufgabenplanung (REQ-006) | Ja | Tasks HA-unabhängig |
| Erntemanagement (REQ-007) | Ja | Reine Domänenlogik |
| IPM-System (REQ-010) | Ja | Manuelle Inspektionen |
| Kalender (REQ-015) | Ja | iCal-Export HA-unabhängig |
| Tankmanagement (REQ-014) | Ja | `source: manual` |
| Pflegeerinnerungen (REQ-022) | Ja | Serverseitige Generierung |

---

## 8. Custom Lovelace Cards

Die `kamerplanter-ha` Integration liefert Custom Lovelace Cards mit, die in `/local/kamerplanter/` (via HACS) oder `/local/` (manuelle Installation) registriert werden. Alle Cards nutzen Kami-SVG-Illustrationen aus `/local/kami/`.

### 8.1 Verzeichnisstruktur

```
custom_components/kamerplanter/
└── www/
    ├── kamerplanter-plant-card.js     # Pflanzen-Card (Phase + Fortschritt)
    ├── kamerplanter-tank-card.js      # Tank-Card (geplant)
    └── kamerplanter-location-card.js  # Standort-Card (geplant)
```

**Registrierung in HA:** Die Cards registrieren sich via `window.customCards.push()` und sind im Card-Picker unter dem Namen sichtbar. Lovelace-Ressourcen werden automatisch via `async_setup_entry` registriert (`/hacsfiles/kamerplanter/...` bei HACS, `/local/...` bei manueller Installation).

### 8.2 custom:kamerplanter-plant-card

Unified Card für Pflanzeninstanzen und Planting Runs. Zeigt Phasenübergänge, Fortschrittsbalken, Kami-Illustrationen und Phasen-Historie.

**Konfiguration:**

| Feld | Typ | Pflicht | Default | Beschreibung |
|------|-----|---------|---------|-------------|
| `device_id` | `string` | Ja | — | HA Device-ID einer Kamerplanter Pflanze / Planting Run |
| `title` | `string` | Nein | Device-Name | Optionaler Titel |
| `show_progress` | `boolean` | Nein | `true` | Fortschrittsbalken (Woche/Tag/%) anzeigen |
| `show_timeline` | `boolean` | Nein | `true` | Phasen-Timeline-Stepper anzeigen |
| `show_next_hint` | `boolean` | Nein | `true` | Nächste-Phase-Hinweis anzeigen |
| `show_stats` | `boolean` | Nein | `true` | Wochen- & Ernte-Statistik anzeigen |
| `show_details` | `boolean` | Nein | `true` | Phasen-Historie-Tabelle anzeigen |

**Konfiguration im Editor:** Device-Picker mit `selector: { device: { integration: "kamerplanter" } }` — zeigt nur Kamerplanter-Devices. Nutzt `ha-form` + Schema-Pattern (UI-NFR-015 §2.1).

**YAML-Beispiel:**

```yaml
type: custom:kamerplanter-plant-card
device_id: abc123def456
title: Northern Lights #3
# Bereiche ein-/ausblenden (alle default: true)
show_progress: true
show_timeline: true
show_next_hint: true
show_details: false    # z.B. kompakte Darstellung ohne Historie
```

**Aufbau der Card (Top → Bottom):**

```
┌──────────────────────────────────────────┐
│  [Kami]  Northern Lights #3    [ 42d ]   │  ← Header: Kami-Icon, Name, Days-Badge
│          Plagron Terra Grow              │  ← Nutrient-Plan-Badge (optional)
├──────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │    12    │ │     3    │ │   44d    │ │  ← Stats: Gesamtwoche, Phasenwoche,
│  │Gesamtwoche│ │Phasenwoche│ │bis Ernte │ │     Tage bis Ernte
│  └──────────┘ └──────────┘ └──────────┘ │
├──────────────────────────────────────────┤
│  Blüte                    Tag 12 / 56    │  ← Progress: Phase-Label, Tag/Woche
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░  │  ← Progress-Bar
│  21%                 44 Tage verbleibend │  ← Prozent + Restzeit
├──────────────────────────────────────────┤
│  (●)──(●)──(●)──(◉)──(○)──(○)          │  ← Timeline-Stepper mit Kami-Markern
│  Keim  Säml  Veg  Blüte Reife Ernte     │  ← Phase-Labels (DE)
│  01.01 15.01 01.02 15.03               │  ← Start-Daten
├──────────────────────────────────────────┤
│  → [Kami] Reife in 6 Wochen             │  ← Next-Phase-Hint mit Countdown
├──────────────────────────────────────────┤
│  Phase          Start       Dauer        │  ← Detail-Tabelle
│  Keimung        01.01.2026  14d          │
│  Sämling        15.01.2026  17d          │
│  Vegetativ      01.02.2026  42d          │
│  ● Blüte        15.03.2026  12d          │  ← Aktuelle Phase markiert
└──────────────────────────────────────────┘
```

**Datenquellen (Entities vom Device):**

| Sensor-Suffix | Verwendung | Abschnitt |
|---------------|-----------|-----------|
| `phase_timeline` | Phasen-Liste, Timeline-Attribute, Progress-Daten | Timeline, Progress, Details |
| `phase` / `status` | Aktuelle Phase (Fallback) | Header, Progress |
| `next_phase` | Nächste Phase (Fallback) | Next-Phase-Hint |
| `nutrient_plan` | Nährstoffplan-Name | Header Badge |
| `days_in_phase` | Tage in aktueller Phase (Fallback) | Header Badge |

**Timeline-Attribute (aus `phase_timeline` Sensor):**

| Attribut | Typ | Beschreibung |
|----------|-----|-------------|
| `current_phase_name` | `str` | Name der aktuellen Phase |
| `days_in_phase` | `int` | Tage in aktueller Phase |
| `phase_week` | `int` | Aktuelle Woche in der Phase |
| `phase_planned_weeks` | `int` | Geplante Gesamtwochen der Phase |
| `phase_remaining_weeks` | `int` | Verbleibende Wochen |
| `phase_progress_pct` | `int` | Fortschritt in Prozent (0–100) |
| `typical_duration_days` | `int` | Typische Dauer der Phase in Tagen |
| `remaining_days` | `int` | Verbleibende Tage |
| `next_plan_phase` | `str` | Nächste Phase aus Nährstoffplan |
| `next_plan_phase_weeks` | `int` | Geplante Wochen der nächsten Phase |
| `weeks_until_next_phase` | `int` | Wochen bis Phasenwechsel |
| `overall_week` | `int` | Gesamtwoche seit Grow-Start |
| `overall_days` | `int` | Gesamttage seit Grow-Start |
| `days_to_harvest` | `int` | Verbleibende Tage bis geplante Ernte (Summe aller Restphasen) |
| `{phase_name}` | `object` | Pro Phase: `{ status, started, date, days }` |

**Phase-Status-Werte:** `completed`, `current`, `upcoming`

**Kami-SVG-Phasen (14):**

`germination`, `seedling`, `vegetative`, `flowering`, `ripening`, `harvest`, `dormancy`, `juvenile`, `climbing`, `mature`, `senescence`, `flushing`, `leaf_phase`, `short_day_induction`

**Deutsche Phase-Labels:**

| Phase-Key | Label |
|-----------|-------|
| `germination` | Keimung |
| `seedling` | Sämling |
| `vegetative` | Vegetativ |
| `flowering` | Blüte |
| `ripening` | Reife |
| `harvest` | Ernte |
| `dormancy` | Ruhephase |
| `flush` / `flushing` | Spülphase / Spülung |
| `drying` | Trocknung |
| `curing` | Curing |
| `leaf_phase` | Blattphase |
| `short_day_induction` | Kurztageinleitung |
| `juvenile` | Juvenil |
| `climbing` | Kletterphase |
| `mature` | Reifephase |
| `senescence` | Seneszenz |

**Bedingte Sichtbarkeit:**

| Abschnitt | Sichtbar wenn |
|-----------|--------------|
| Stats-Kacheln | `overall_week`, `phase_week` oder `days_to_harvest` vorhanden |
| Progress-Bar | `phase_week` + `phase_planned_weeks` vorhanden und > 0 |
| Days-Badge | `days_in_phase` vorhanden und nicht `unknown` |
| Nutrient-Plan-Badge | `nutrient_plan` vorhanden und nicht `None`/`unknown` |
| Next-Phase-Hint | `next_plan_phase` + `weeks_until_next_phase` vorhanden ODER `next_phase` Sensor vorhanden |
| Detail-Tabelle | Mindestens eine Phase mit Status `completed` oder `current` |

**Grid-Optionen:** `columns: 6, min_columns: 3, rows: 8, min_rows: 4` (Masonry: `getCardSize() = 8`)
