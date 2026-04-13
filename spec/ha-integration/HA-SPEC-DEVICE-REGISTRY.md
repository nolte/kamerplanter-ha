# Spezifikation: HA Device Registry & Entity-Mapping

```yaml
ID: HA-SPEC-DEVICE
Titel: Home Assistant Device Registry — Verbindliche Device- und Entity-Definitionen
Status: Spezifiziert
Version: 1.0
Datum: 2026-04-04
Abhaengigkeiten: [HA-SPEC-ENTITY, HA-SPEC-CONFIG-LIFECYCLE]
Scope: entity.py, sensor.py, binary_sensor.py, button.py, calendar.py, todo.py
Style Guide: spec/style-guides/HA-INTEGRATION.md
```

---

## 1. Ziel

Verbindliche Definition aller Home Assistant Devices und ihrer zugehoerigen Entities fuer die Kamerplanter Custom Integration. Dieses Dokument ist die **Single Source of Truth** fuer:

- Welche HA-Devices existieren und wie sie identifiziert werden
- Welche Entities zu welchem Device gehoeren
- Welche Datenquellen (Coordinator / API) jede Entity speisen
- Die Device-Hierarchie (Hub → Child Devices)

---

## 2. Device-Hierarchie

```
Kamerplanter Server (Hub)
├── Plant Instance Device (1 pro aktive Pflanze)
├── Planting Run Device (1 pro aktiver Durchlauf)
├── Location Device (1 pro Standort)
└── Tank Device (1 pro Tank)
```

Alle Child-Devices nutzen `via_device` zum Server-Hub. HA zeigt sie dadurch in der Device-Ansicht hierarchisch unter dem Hub an.

---

## 3. Device-Definitionen

### 3.1 Server Device (Hub)

Das zentrale Hub-Device repraesentiert die Kamerplanter-Instanz. Es ist der Ankerpunkt fuer alle globalen Entities (Tasks, Kalender, Alerts) und Eltern-Device aller anderen Geraete.

| Eigenschaft | Wert |
|-------------|------|
| **Identifier** | `(DOMAIN, entry.entry_id)` |
| **Name** | `"Kamerplanter"` |
| **Manufacturer** | `"Kamerplanter"` |
| **Model** | `"Plant Management Server"` |
| **via_device** | — (ist Hub) |

**Coordinator-Zuordnung:** AlertCoordinator, TaskCoordinator

---

### 3.2 Plant Instance Device

Ein Device pro aktiver Pflanzeninstanz. Wird dynamisch erstellt/entfernt wenn Pflanzen hinzugefuegt oder archiviert werden.

| Eigenschaft | Wert |
|-------------|------|
| **Identifier** | `(DOMAIN, f"{entry.entry_id}_plant_{plant_key}")` |
| **Name** | `plant_name` oder `instance_id` oder `key` (Fallback-Kette) |
| **Manufacturer** | `"Kamerplanter"` |
| **Model** | `"Plant Instance"` |
| **via_device** | Server Device |

**Coordinator-Zuordnung:** PlantCoordinator

**Wann sichtbar:** Nur fuer Pflanzen ohne `removed_on` (aktive Pflanzen). Archivierte Pflanzen werden als `unavailable` markiert.

---

### 3.3 Planting Run Device

Ein Device pro aktivem Pflanzdurchlauf (Status != `completed` / `cancelled`).

| Eigenschaft | Wert |
|-------------|------|
| **Identifier** | `(DOMAIN, f"{entry.entry_id}_run_{run_key}")` |
| **Name** | `run.name` oder `run.key` (Fallback) |
| **Manufacturer** | `"Kamerplanter"` |
| **Model** | `"Planting Run ({run_type})"` — z.B. `"Planting Run (monoculture)"` |
| **via_device** | Server Device |

**Coordinator-Zuordnung:** RunCoordinator

**Wann sichtbar:** Nur fuer Runs mit Status `planned`, `active` oder `harvesting`.

---

### 3.4 Location Device

Ein Device pro Standort (flache Liste ueber alle Sites hinweg).

| Eigenschaft | Wert |
|-------------|------|
| **Identifier** | `(DOMAIN, f"{entry.entry_id}_location_{location_key}")` |
| **Name** | `location.name` oder `location_key` (Fallback) |
| **Manufacturer** | `"Kamerplanter"` |
| **Model** | `"Location ({location_type_key})"` — z.B. `"Location (grow_tent)"` |
| **via_device** | Server Device |

**Coordinator-Zuordnung:** LocationCoordinator

**Hinweis:** Die Location-Hierarchie (Site → Room → Tent → Slot) wird in HA flach dargestellt. Die Eltern-Kind-Beziehung zwischen Locations wird **nicht** ueber `via_device` abgebildet — alle Locations sind direkte Kinder des Server-Devices.

---

### 3.5 Tank Device

Ein Device pro Tank. Optionale Zuordnung zu einem Standort ueber `suggested_area`.

| Eigenschaft | Wert |
|-------------|------|
| **Identifier** | `(DOMAIN, f"{entry.entry_id}_tank_{tank_key}")` |
| **Name** | `tank.name` oder `tank.key` (Fallback) |
| **Manufacturer** | `"Kamerplanter"` |
| **Model** | `"Tank ({tank_type}) {volume_liters}L"` — z.B. `"Tank (nutrient_solution) 50L"` |
| **suggested_area** | Location-Name (falls Tank einem Standort zugeordnet) |
| **via_device** | Server Device |

**Coordinator-Zuordnung:** LocationCoordinator (Tanks werden als Teil der Location-Daten enriched)

---

## 4. Entity-Definitionen pro Device

### 4.1 Server Device Entities

#### Sensors

| translation_key | Beschreibung | Unit | state_class | device_class | EntityCategory | Datenquelle |
|----------------|-------------|------|-------------|-------------|----------------|-------------|
| `tasks_due_today` | Anzahl heute faelliger Aufgaben | — | MEASUREMENT | — | — | TaskCoordinator: `pending_tasks` gefiltert nach `due_date == today` |
| `tasks_overdue` | Anzahl ueberfaelliger Aufgaben | — | MEASUREMENT | — | — | AlertCoordinator: `len(overdue_tasks)` |
| `next_watering` | Naechster Giesstermin (Datum+Pflanze) | — | — | — | — | PlantCoordinator: fruehestes `_watering_next_date` ueber alle Pflanzen |

#### Binary Sensors

| translation_key | Beschreibung | device_class | EntityCategory | Datenquelle |
|----------------|-------------|-------------|----------------|-------------|
| `needs_attention` | Mind. eine Pflanze braucht Aufmerksamkeit | PROBLEM | — | AlertCoordinator: `len(overdue_tasks) > 0` |
| `sensor_offline` | Mind. ein verknuepfter Sensor ist offline | CONNECTIVITY | DIAGNOSTIC | AlertCoordinator: Sensor-Health-Check |
| `care_overdue` | Mind. eine Pflegeerinnerung ist ueberfaellig | PROBLEM | — | PlantCoordinator: Care-Overdue-Flag aus Pflanzdaten |

#### Buttons

| translation_key | Beschreibung | EntityCategory | Aktion |
|----------------|-------------|----------------|--------|
| `refresh_all` | Alle Daten sofort aktualisieren | CONFIG | Ruft `async_request_refresh()` auf allen 5 Coordinators auf |

#### Calendars

| translation_key | Beschreibung | Datenquelle |
|----------------|-------------|-------------|
| `phases` | Phasen-Kalender (Phasenuebergaenge aller Pflanzen) | PlantCoordinator: `_phase_history` aller Pflanzen → CalendarEvent |
| `tasks` | Aufgaben-Kalender (faellige Tasks als Events) | TaskCoordinator: `pending_tasks` → CalendarEvent |

#### Todo Lists

| translation_key | Beschreibung | Datenquelle | Aktionen |
|----------------|-------------|-------------|----------|
| `tasks` | Offene Aufgaben als Todo-Items | TaskCoordinator: `pending_tasks` | Abschliessen via `async_complete_task()` |

---

### 4.2 Plant Instance Device Entities

#### Sensors

| translation_key | Beschreibung | Unit | state_class | Datenquelle |
|----------------|-------------|------|-------------|-------------|
| `phase` | Aktuelle Wachstumsphase | — | — | `plant["current_phase"]` |
| `days_in_phase` | Tage in aktueller Phase | `d` | MEASUREMENT | Berechnet: `today - plant["current_phase_started_at"]` |
| `nutrient_plan` | Name des zugeordneten Naehrstoffplans | — | — | `plant["_nutrient_plan"]["name"]` |
| `active_channels` | Anzahl aktiver Duengekanal | — | — | `len(plant["_active_channels"])`, Details als Attribute |
| `phase_timeline` | Aktuelle Phase als State, Historie als Attribute | — | — | `plant["_phase_history"]` als extra_state_attributes |
| `next_phase` | Naechste erwartete Phase | — | — | Berechnet aus `_phase_history` + Phasendefinition |
| `days_until_watering` | Tage bis naechste Bewässerung | `d` | MEASUREMENT | `plant["_watering_interval_days"]` − Tage seit `plant["_watering_last_date"]` |
| `channel_mix` (dynamisch) | Mischverhaeltnis pro Duengekanal | — | — | `plant["_current_dosages"]["channels"][i]` — 1 Entity pro aktivem Kanal |

**Dynamische Entities:** `channel_mix` wird pro aktivem Kanal erstellt. Der `unique_id` enthaelt die Channel-ID: `{entry_id}_kp_{plant_slug}_ch_{channel_id}_mix`.

#### Binary Sensors

| translation_key | Beschreibung | device_class | Datenquelle |
|----------------|-------------|-------------|-------------|
| `needs_attention` | Pflanze braucht Aufmerksamkeit | PROBLEM | AlertCoordinator: Pflanze hat ueberfaellige Tasks oder Care-Alerts |

---

### 4.3 Planting Run Device Entities

#### Sensors

| translation_key | Beschreibung | Unit | state_class | Datenquelle |
|----------------|-------------|------|-------------|-------------|
| `run_status` | Aktueller Run-Status | — | — | `run["status"]` |
| `plant_count` | Anzahl Pflanzen im Run | — | MEASUREMENT | `run["actual_quantity"]` |
| `nutrient_plan` | Name des Naehrstoffplans | — | — | `run["_nutrient_plan"]["name"]` |
| `phase_timeline` | Aktuelle Phase als State, Phasen-Historie als Attribute | — | — | `run["_timeline"]` |
| `next_phase` | Naechste erwartete Phase | — | — | Berechnet aus `_timeline` + `_phase_entries` |
| `days_until_watering` | Tage bis naechste Bewässerung | `d` | MEASUREMENT | `run["_watering_schedule"]` |
| `channel_mix` (dynamisch) | Mischverhaeltnis pro Duengekanal | — | — | `run["_current_phase_entries"]["delivery_channels"]` — 1 Entity pro Kanal |

---

### 4.4 Location Device Entities

#### Sensors

| translation_key | Beschreibung | Unit | state_class | Datenquelle |
|----------------|-------------|------|-------------|-------------|
| `location_type` | Standorttyp | — | — | `loc["location_type_key"]` |
| `active_runs` | Anzahl aktiver Durchlaeufe | — | MEASUREMENT | `loc["_active_run_count"]` |
| `active_plants` | Anzahl aktiver Pflanzen | — | MEASUREMENT | `loc["_active_plant_count"]` |
| `phase` | Phase des Primaer-Runs | — | — | `loc["_primary_run"]["current_phase"]` — nur wenn genau 1 aktiver Run |
| `days_in_phase` | Tage in Phase des Primaer-Runs | `d` | MEASUREMENT | Berechnet aus `_primary_run` Timeline |
| `nutrient_plan` | Naehrstoffplan des Primaer-Runs | — | — | `loc["_primary_run"]["_nutrient_plan"]["name"]` |
| `next_phase` | Naechste Phase des Primaer-Runs | — | — | `loc["_primary_run"]["_timeline"]` |
| `phase_timeline` | Phasen-Historie des Primaer-Runs | — | — | `loc["_primary_run"]["_timeline"]` als extra_state_attributes |
| `channel_mix` (dynamisch) | Mischverhaeltnis pro Duengekanal des Primaer-Runs | — | — | `loc["_primary_run"]["_current_phase_entries"]["delivery_channels"]` |
| `tank_info` | Zusammenfassung des zugeordneten Tanks | — | — | `loc["_tanks"][0]` — Name, Typ, letzter Fill |
| `tank_volume` | Volumen des zugeordneten Tanks | `L` | MEASUREMENT | `loc["_tanks"][0]["volume_liters"]` |

#### Binary Sensors

| translation_key | Beschreibung | device_class | Datenquelle |
|----------------|-------------|-------------|-------------|
| `needs_attention` | Standort braucht Aufmerksamkeit | PROBLEM | Aggregiert: ueberfaellige Tasks oder Care-Alerts an diesem Standort |

---

### 4.5 Tank Device Entities

#### Sensors

| translation_key | Beschreibung | Unit | state_class | device_class | Datenquelle |
|----------------|-------------|------|-------------|-------------|-------------|
| `tank_info` | Zusammenfassung: Name, Typ, letzter Fill, verknuepfte HA-Sensoren | — | — | — | Tank-Daten + `_latest_fill` + `_ha_sensors` |
| `tank_volume` | Tankvolumen (Kapazitaet) | `L` | MEASUREMENT | VOLUME | `tank["volume_liters"]` |

**Geplante Erweiterungen (wenn TankState-API verfuegbar):**

| translation_key | Beschreibung | Unit | state_class | device_class | Datenquelle |
|----------------|-------------|------|-------------|-------------|-------------|
| `fill_level` | Fuellstand in Prozent | `%` | MEASUREMENT | — | `TankState.fill_level_percent` |
| `ec` | EC-Wert der Naehrloesung | `mS/cm` | MEASUREMENT | — | `TankState.ec_ms` |
| `ph` | pH-Wert | `pH` | MEASUREMENT | — | `TankState.ph` |
| `water_temp` | Wassertemperatur | `°C` | MEASUREMENT | TEMPERATURE | `TankState.water_temp_celsius` |
| `solution_age_days` | Alter der Naehrloesung in Tagen | `d` | MEASUREMENT | — | Berechnet aus letztem `full_change` TankFillEvent |

---

## 5. Coordinator → Device → Entity Zuordnung

| Coordinator | Polling | Devices | Entity-Typen |
|-------------|---------|---------|-------------|
| **PlantCoordinator** | 300s | Plant Instance | sensor (8 + dynamisch), binary_sensor (1) |
| **RunCoordinator** | 300s | Planting Run | sensor (6 + dynamisch) |
| **LocationCoordinator** | 300s | Location, Tank | sensor (11 + dynamisch), binary_sensor (1), sensor (2 Tank) |
| **AlertCoordinator** | 60s | Server | binary_sensor (3), sensor (1 tasks_overdue) |
| **TaskCoordinator** | 300s | Server | sensor (1 tasks_due_today), calendar (2), todo (1) |

---

## 6. unique_id-Schema

Alle `unique_id`-Werte folgen diesem Muster (Entity-Registry-Kompatibilitaet):

```
{entry_id}_kp_{device_slug}_{entity_suffix}
```

| Device-Typ | Slug-Muster | Beispiel unique_id |
|-----------|-------------|-------------------|
| Server | — | `{entry_id}_kp_tasks_due_today` |
| Plant | `{plant_slug}` | `{entry_id}_kp_northern_lights_01_phase` |
| Run | `run_{run_slug}` | `{entry_id}_kp_run_tomato_spring_2026_status` |
| Location | `loc_{location_slug}` | `{entry_id}_kp_loc_greenhouse_1_active_runs` |
| Tank | `tank_{tank_slug}` | `{entry_id}_kp_tank_main_reservoir_volume` |
| Dynamisch (Channel) | `{parent_slug}_ch_{channel_id}` | `{entry_id}_kp_northern_lights_01_ch_drip_a_mix` |

**Slug-Generierung:** `_slugify_key(arango_key)` — ersetzt `-` durch `_`, lowercase.

**WICHTIG:** Das `unique_id`-Format darf **nie** geaendert werden, da HA die Entity-Registry darauf basiert. Aenderungen fuehren zu verwaisten Entities und gebrochenen Automationen.

### 6.1 Englische entity_ids (PFLICHT)

HA generiert `entity_id`-Slugs aus dem uebersetzten Entity-Namen der **Systemsprache** bei Erstregistrierung. Damit entity_ids sprachunabhaengig und stabil bleiben:

- **HA-Systemsprache MUSS `en` sein** (`configuration.yaml: language: en`)
- `strings.json` liefert die englischen Namen (Source of Truth fuer entity_ids)
- `translations/de.json` liefert die deutschen UI-Anzeigenamen (nur Frontend)
- Nutzer koennen ihre persoenliche HA-UI-Sprache auf Deutsch stellen

Beispiel bei korrekter Konfiguration (`language: en`):
```
sensor.northern_lights_01_days_until_watering   ← korrekt (englisch)
```

Beispiel bei falscher Konfiguration (`language: de`):
```
sensor.northern_lights_01_tage_bis_giessen      ← FALSCH (deutsch, instabil)
```

---

## 7. Device Lifecycle

### 7.1 Erstellung

Devices werden **automatisch** bei der ersten Entity-Registrierung erstellt. Wenn der Coordinator neue Pflanzen/Runs/Locations/Tanks liefert, werden die zugehoerigen Entities in `async_setup_entry` registriert und HA erstellt das Device.

### 7.2 Unavailable

Wenn ein Device-Objekt (z.B. Pflanze) aus den Coordinator-Daten verschwindet (archiviert, geloescht), werden alle zugehoerigen Entities als `unavailable` markiert via:

```python
@property
def available(self) -> bool:
    if not super().available:
        return False
    return any(p["key"] == self._plant_key for p in self.coordinator.data)
```

### 7.3 Entfernung

Devices werden **nicht** automatisch entfernt. Der Nutzer kann verwaiste Devices manuell in der HA Device Registry loeschen. Bei einem Config-Entry-Reload werden alle Entities neu aufgebaut.

### 7.4 Dynamische Entities (Channel Mix)

Channel-Entities werden bei jedem Coordinator-Update dynamisch ermittelt. Neue Kanaele erzeugen neue Entities, weggefallene Kanaele werden `unavailable`. Die Discovery erfolgt in `async_setup_entry` ueber die enriched Coordinator-Daten.

---

## 8. Device-Info in Lovelace Cards

Die Custom Lovelace Cards (plant-card, tank-card, mix-card) verwenden die Device-Identifier um Entities zu gruppieren:

| Card | Primaer-Device | Entities |
|------|---------------|----------|
| `kamerplanter-plant-card` | Plant Instance | phase, days_in_phase, nutrient_plan, channel_mix(s), needs_attention |
| `kamerplanter-mix-card` | Plant Instance / Run | channel_mix(s), nutrient_plan, active_channels |
| `kamerplanter-tank-card` | Tank | tank_info, tank_volume, (fill_level, ec, ph, water_temp) |
| `kamerplanter-care-card` | Server | tasks_due_today, tasks_overdue, care_overdue, needs_attention |

---

## 9. Zusammenfassung: Entity-Zaehlung

| Device-Typ | Sensors | Binary Sensors | Buttons | Calendars | Todo | Gesamt |
|-----------|---------|---------------|---------|-----------|------|--------|
| Server | 3 | 3 | 1 | 2 | 1 | **10** |
| Plant Instance | 7 + n Channels | 1 | — | — | — | **8 + n** |
| Planting Run | 6 + n Channels | — | — | — | — | **6 + n** |
| Location | 9 + n Channels + 2 Tank | 1 | — | — | — | **12 + n** |
| Tank | 2 (+ 5 geplant) | — | — | — | — | **2 (7)** |

**Typisches Setup** (3 Pflanzen, 1 Run, 2 Locations, 1 Tank, je 2 Kanaele):
- 10 (Server) + 3×10 (Pflanzen) + 8 (Run) + 2×14 (Locations) + 2 (Tank) = **76 Entities**
