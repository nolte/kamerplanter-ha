# Spezifikation: Entity-Architektur Refactoring

```yaml
ID: HA-SPEC-ENTITY
Titel: Entity-Architektur Migration auf HA Best Practices
Status: Spezifiziert
Version: 1.0
Datum: 2026-04-03
Behebt: GAP-002, GAP-003, GAP-011, GAP-012, GAP-013, GAP-014, GAP-015, GAP-029, GAP-030, GAP-031
Abhaengigkeiten: HA-SPEC-CONFIG-LIFECYCLE (runtime_data muss zuerst migriert sein)
Scope: sensor.py, binary_sensor.py, button.py, calendar.py, todo.py, entity.py (neu), icons.json (neu)
Style Guide: spec/style-guides/HA-INTEGRATION.md
```

---

## 1. Ziel

Migration der Entity-Architektur von 40+ individuellen Klassen in einer 1907-Zeilen-Datei (`sensor.py`) auf das HA-Standard-Pattern mit:
- Einer gemeinsamen Base Entity (`entity.py`)
- EntityDescription-gesteuerten Sensor-Definitionen
- Automatischer `entity_id`-Generierung durch HA (kein manuelles Setzen)
- `translation_key` fuer alle Entity-Names und States
- `icons.json` fuer zustandsabhaengige Icons
- `EntityCategory` fuer Config/Diagnostic-Entities
- Device-Hierarchie mit `via_device`

---

## 2. Neue Datei: entity.py

Erstelle `custom_components/kamerplanter/entity.py`:

```python
"""Base entity for the Kamerplanter integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN


class KamerplanterEntity(CoordinatorEntity):
    """Base class for all Kamerplanter entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = device_info
        self._entry_id = entry_id


# --- DeviceInfo Factory Functions ---

def server_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Create DeviceInfo for the Kamerplanter server (hub device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Kamerplanter",
        manufacturer="Kamerplanter",
        model="Plant Management Server",
    )


def plant_device_info(entry: ConfigEntry, plant: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a plant instance (child device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_plant_{plant['key']}")},
        name=plant.get("plant_name") or plant.get("instance_id") or plant["key"],
        manufacturer="Kamerplanter",
        model="Plant Instance",
        via_device=(DOMAIN, entry.entry_id),
    )


def location_device_info(entry: ConfigEntry, loc: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a location (child device)."""
    loc_key = loc.get("key") or loc.get("_key", "")
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_loc_{loc_key}")},
        name=loc.get("name") or loc_key,
        manufacturer="Kamerplanter",
        model="Location",
        via_device=(DOMAIN, entry.entry_id),
    )


def run_device_info(entry: ConfigEntry, run: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a planting run (child device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_run_{run['key']}")},
        name=run.get("name") or run["key"],
        manufacturer="Kamerplanter",
        model="Planting Run",
        via_device=(DOMAIN, entry.entry_id),
    )


def tank_device_info(entry: ConfigEntry, tank: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a tank (child device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_tank_{tank.get('key', '')}")},
        name=tank.get("name") or tank.get("key", ""),
        manufacturer="Kamerplanter",
        model="Tank",
        via_device=(DOMAIN, entry.entry_id),
    )


def _slugify_key(key: str) -> str:
    """Convert ArangoDB key to entity-id-safe slug."""
    return key.replace("-", "_").lower()
```

---

## 3. EntityDescription-Definitionen

### 3.1 Plant Sensors

| key | translation_key | device_class | unit | state_class | Datenquelle |
|-----|----------------|-------------|------|-------------|-------------|
| `phase` | `phase` | — | — | — | `plant["current_phase"]` |
| `days_in_phase` | `days_in_phase` | — | `d` | MEASUREMENT | Berechnet aus `current_phase_started_at` |
| `vpd_target` | `vpd_target` | — | `kPa` | MEASUREMENT | `_nutrient_plan` oder RequirementProfile |
| `ec_target` | `ec_target` | — | `mS/cm` | MEASUREMENT | `_current_dosages.target_ec_ms` |
| `nutrient_plan` | `nutrient_plan` | — | — | — | `_nutrient_plan.name` |
| `active_channels` | `active_channels` | — | — | — | `_active_channels` (Count + Details als Attribute) |
| `phase_timeline` | `phase_timeline` | — | — | — | `_phase_history` (als Attribute) |
| `next_phase` | `next_phase` | — | — | — | Berechnet aus Timeline |
| `{channel}_mix` | `channel_mix` | — | — | — | `_current_dosages.channels[]` (dynamisch) |

### 3.2 Run Sensors

| key | translation_key | device_class | unit | state_class |
|-----|----------------|-------------|------|-------------|
| `status` | `run_status` | — | — | — |
| `plant_count` | `plant_count` | — | — | MEASUREMENT |
| `nutrient_plan` | `nutrient_plan` | — | — | — |
| `phase_timeline` | `phase_timeline` | — | — | — |
| `next_phase` | `next_phase` | — | — | — |
| `{channel}_mix` | `channel_mix` | — | — | — |

### 3.3 Location Sensors

| key | translation_key | device_class | unit | state_class |
|-----|----------------|-------------|------|-------------|
| `type` | `location_type` | — | — | — |
| `active_run_count` | `active_runs` | — | — | MEASUREMENT |
| `active_plant_count` | `active_plants` | — | — | MEASUREMENT |
| `run_phase` | `phase` | — | — | — |
| `run_days_in_phase` | `days_in_phase` | — | `d` | MEASUREMENT |

### 3.4 Tank Sensors

| key | translation_key | device_class | unit | state_class |
|-----|----------------|-------------|------|-------------|
| `info` | `tank_info` | — | — | — |
| `volume` | `tank_volume` | VOLUME | `L` | MEASUREMENT |
| `fill_level` | `fill_level` | — | `%` | MEASUREMENT |
| `ec` | `ec_target` | — | `mS/cm` | MEASUREMENT |
| `ph` | — | — | `pH` | MEASUREMENT |
| `water_temp` | — | TEMPERATURE | `°C` | MEASUREMENT |
| `solution_age_days` | — | — | `d` | MEASUREMENT |

### 3.5 Global Sensors (Server Device)

| key | translation_key | state_class |
|-----|----------------|-------------|
| `tasks_due_today` | `tasks_due_today` | MEASUREMENT |
| `tasks_overdue` | `tasks_overdue` | MEASUREMENT |
| `next_watering` | `next_watering` | — |

### 3.6 Binary Sensors

| key | translation_key | device_class | EntityCategory |
|-----|----------------|-------------|----------------|
| `needs_attention` | `needs_attention` | PROBLEM | — |
| `sensor_offline` | `sensor_offline` | CONNECTIVITY | DIAGNOSTIC |
| `care_overdue` | `care_overdue` | PROBLEM | — |
| `loc_needs_attention` | `needs_attention` | PROBLEM | — |

### 3.7 Button

| key | translation_key | EntityCategory |
|-----|----------------|----------------|
| `refresh_all` | `refresh_all` | CONFIG |

---

## 4. Migration: entity_id

### 4.1 Vorher (VERBOTEN)

```python
self.entity_id = f"sensor.kp_{slug}_phase"
```

### 4.2 Nachher

```python
# Kein entity_id setzen!
# HA generiert automatisch aus Device-Name + translation_key
self._attr_unique_id = f"{entry.entry_id}_plant_{slug}_phase"
self._attr_translation_key = "phase"
```

### 4.3 Migrationsstrategie

Da bestehende Automationen moeglicherweise auf die alten `entity_id`s referenzieren (`sensor.kp_xxx_phase`), sollte die Migration:

1. Die **unique_id** beibehalten (gleicher Wert wie bisher)
2. Die **entity_id** nicht mehr manuell setzen
3. HA wird die entity_id aus der Entity Registry wiederherstellen (basierend auf unique_id)
4. Nur bei komplett neuen Entities wird HA eine neue entity_id generieren

**Risiko:** Bei Entities deren unique_id-Format sich aendert, geht die Entity-Registry-Zuordnung verloren. Daher: **unique_id-Format NICHT aendern**, nur `self.entity_id = ...` entfernen.

---

## 5. RestoreEntity-Verwendung

### 5.1 Behalten (sinnvoll)

- `binary_sensor.*` — Zustand zwischen Neustarts relevant (z.B. "Needs Attention" bleibt true)
- `TasksDueTodaySensor` / `TasksOverdueSensor` — Zeigen Daten die erst beim naechsten Poll verfuegbar sind
- `NextWateringSensor` — Naechster Giesszeitpunkt bleibt relevant

### 5.2 Entfernen (unnoetig)

- Plant-Sensors (Phase, Days in Phase, VPD Target, EC Target, Nutrient Plan, Active Channels, Phase Timeline, Next Phase) — Werden beim naechsten 5-Minuten-Poll sofort ueberschrieben
- Run-Sensors — Gleicher Grund
- Location-Sensors — Gleicher Grund
- Tank-Sensors — Gleicher Grund

### 5.3 Umsetzung

Base Entity `KamerplanterEntity` erbt **nicht** von `RestoreEntity`. Nur die Entities die es benoetigen, erben zusaetzlich:

```python
class PlantNeedsAttentionSensor(KamerplanterEntity, RestoreEntity, BinarySensorEntity):
    ...
```

---

## 6. Entity Availability

```python
class KamerplanterPlantSensor(KamerplanterEntity, SensorEntity):
    @property
    def available(self) -> bool:
        """Entity is available only if the plant exists in coordinator data."""
        if not super().available:
            return False
        if not self.coordinator.data:
            return False
        return any(p["key"] == self._plant_key for p in self.coordinator.data
                   if not p.get("removed_on"))
```

---

## 7. Datei-Aufteilung

### 7.1 Zielstruktur

| Datei | Inhalt | Geschaetzte Zeilen |
|-------|--------|-------------------|
| `entity.py` | KamerplanterEntity + DeviceInfo-Factories + _slugify_key | ~100 |
| `sensor.py` | EntityDescription-Definitionen + Setup + generische Sensor-Klassen | ~400 |
| `binary_sensor.py` | Binary-Sensor-Entities (bestehend, angepasst) | ~150 |
| `button.py` | Refresh-Button (bestehend, angepasst) | ~30 |
| `calendar.py` | Kalender-Entities (bestehend, angepasst) | ~200 |
| `todo.py` | Todo-Entity (bestehend, angepasst) | ~80 |

### 7.2 Imports aendern

Alle Plattform-Dateien importieren aus `entity.py` statt aus `sensor.py`:

```python
# Vorher (binary_sensor.py):
from .sensor import _slugify_key, plant_device_info, server_device_info, location_device_info

# Nachher:
from .entity import KamerplanterEntity, _slugify_key, plant_device_info, server_device_info, location_device_info
```

---

## 8. Akzeptanzkriterien

- [ ] `entity.py` existiert mit `KamerplanterEntity` + 5 DeviceInfo-Factories
- [ ] Alle Plattform-Dateien erben von `KamerplanterEntity`
- [ ] Kein `self.entity_id = ...` mehr in irgendeiner Entity
- [ ] Alle Entities haben `_attr_translation_key`
- [ ] `strings.json` enthaelt `entity.<platform>.<key>.name` + `.state` fuer Enums
- [ ] `icons.json` existiert mit Entity- und Service-Icons
- [ ] Alle Devices haben `via_device` zum Server-Device
- [ ] `sensor.py` ist unter 500 Zeilen
- [ ] `RestoreEntity` nur auf Binary-Sensors und Task-Sensors
- [ ] `EntityCategory.CONFIG` auf Button, `EntityCategory.DIAGNOSTIC` auf Sensor-Offline
- [ ] Bestehende `unique_id`-Formate sind **nicht** veraendert (Entity-Registry-Kompatibilitaet)
