# Spezifikation: Coordinator-Optimierung

```yaml
ID: HA-SPEC-COORDINATOR
Titel: DataUpdateCoordinator-Optimierung und API-Call-Reduktion
Status: Spezifiziert
Version: 1.0
Datum: 2026-04-03
Behebt: GAP-005, GAP-006, GAP-027, GAP-028, GAP-036
Abhaengigkeiten: HA-SPEC-CONFIG-LIFECYCLE (runtime_data muss verfuegbar sein)
Scope: coordinator.py, sensor.py (Plattform-Dateien), const.py
Style Guide: spec/style-guides/HA-INTEGRATION.md §9
```

---

## 1. Ziel

Optimierung der 5 DataUpdateCoordinators:
- `_async_setup()` fuer einmaliges Laden von Stammdaten
- `always_update=False` um unnoetige Entity-Updates zu vermeiden
- `async_timeout` fuer jeden API-Call
- `config_entry` Parameter an Coordinator uebergeben
- API-Call-Reduktion von ~41 Calls/Poll (10 Pflanzen) auf ~10 Calls/Poll
- `PARALLEL_UPDATES` Konstante auf Plattform-Dateien

---

## 2. Allgemeine Coordinator-Anpassungen

### 2.1 Basis-Constructor (alle 5 Coordinators)

**Vorher:**
```python
class KamerplanterPlantCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    def __init__(self, hass, entry, api):
        interval = entry.options.get(CONF_POLL_PLANTS, DEFAULT_POLL_PLANTS)
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_plants",
            update_interval=timedelta(seconds=interval),
        )
```

**Nachher:**
```python
class KamerplanterPlantCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    def __init__(self, hass, entry, api):
        interval = entry.options.get(CONF_POLL_PLANTS, DEFAULT_POLL_PLANTS)
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_plants",
            config_entry=entry,                    # ★ Pflicht-Parameter
            update_interval=timedelta(seconds=interval),
            always_update=False,                   # ★ Nur Callback bei Datenaenderung
        )
        self.api = api
```

### 2.2 Timeout fuer alle API-Calls

```python
import async_timeout

async def _async_update_data(self) -> list[dict[str, Any]]:
    try:
        async with async_timeout.timeout(30):
            return await self._fetch_and_enrich()
    except TimeoutError as err:
        raise UpdateFailed("API request timed out") from err
    except KamerplanterAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except KamerplanterConnectionError as err:
        raise UpdateFailed(str(err)) from err
```

---

## 3. PlantCoordinator: _async_setup + API-Reduktion

### 3.1 _async_setup fuer Stammdaten

```python
async def _async_setup(self) -> None:
    """Load static data once (fertilizer names for dosage enrichment)."""
    try:
        fertilizers = await self.api.async_get_fertilizers()
        self._fert_lookup: dict[str, str] = {
            f.get("key", ""): f.get("product_name", f.get("name", ""))
            for f in fertilizers
        }
    except KamerplanterConnectionError:
        self._fert_lookup = {}
        _LOGGER.debug("Could not pre-load fertilizer names")
```

### 3.2 _async_update_data — Optimiert

**Vorher (41+ Calls bei 10 Pflanzen):**
```python
plants = await self.api.async_get_plants()        # 1 Call
for plant in plants:                               # 10 Pflanzen:
    plan = await self.api.async_get_plant_nutrient_plan(key)      # +10
    dosages = await self.api.async_get_plant_current_dosages(key)  # +10
    channels = await self.api.async_get_plant_active_channels(key) # +10
    history = await self.api.async_get_plant_phase_history(key)    # +10
# = 41 Calls
```

**Nachher (Bulk-Ansatz):**

Option A — **Backend Bulk-Endpoint** (empfohlen, wenn Backend angepasst werden kann):

```python
# Neuer Backend-Endpoint: GET /api/v1/t/{slug}/plant-instances?enriched=true
# Liefert Pflanzen mit _nutrient_plan, _current_dosages, _phase_history in einem Call
plants = await self.api.async_get_plants_enriched()  # 1 Call statt 41
```

Option B — **Parallele Enrichment-Calls** (ohne Backend-Aenderung):

```python
import asyncio

async def _async_update_data(self) -> list[dict[str, Any]]:
    async with async_timeout.timeout(30):
        plants = await self.api.async_get_plants()
        active_plants = [p for p in plants if not p.get("removed_on")]

        # Paralleles Enrichment statt sequentiell
        enrichment_tasks = [
            self._enrich_plant(plant) for plant in active_plants
        ]
        await asyncio.gather(*enrichment_tasks, return_exceptions=True)

        return plants

async def _enrich_plant(self, plant: dict[str, Any]) -> None:
    """Enrich a single plant with nutrient plan, dosages, and history."""
    key = plant["key"]
    started = plant.get("current_phase_started_at")

    # Nutrient plan
    try:
        plant["_nutrient_plan"] = await self.api.async_get_plant_nutrient_plan(key)
    except Exception:
        plant["_nutrient_plan"] = None

    # Current dosages (nur wenn Plan und Phase vorhanden)
    if started and plant.get("_nutrient_plan"):
        week = _calc_current_week(started)
        try:
            plant["_current_dosages"] = await self.api.async_get_plant_current_dosages(key, week)
        except Exception:
            plant["_current_dosages"] = None
        try:
            plant["_active_channels"] = await self.api.async_get_plant_active_channels(key, week)
        except Exception:
            plant["_active_channels"] = []

    # Phase history
    try:
        plant["_phase_history"] = await self.api.async_get_plant_phase_history(key)
    except Exception:
        plant["_phase_history"] = []
```

---

## 4. LocationCoordinator: _async_setup + Reduktion

### 4.1 Problem

Der LocationCoordinator ist der teuerste: Pro Location werden Sites, Trees, Runs, Slots, Plants, Plans, Entries, Timelines, Tanks, Tank-Fills, Tank-Sensors geladen.

### 4.2 _async_setup

```python
async def _async_setup(self) -> None:
    """Pre-load fertilizer names and tank list (rarely change)."""
    try:
        fertilizers = await self.api.async_get_fertilizers()
        self._fert_lookup = {f.get("key", ""): f.get("product_name", f.get("name", "")) for f in fertilizers}
    except KamerplanterConnectionError:
        self._fert_lookup = {}

    try:
        self._all_tanks = await self.api.async_get_tanks()
    except KamerplanterConnectionError:
        self._all_tanks = []
```

### 4.3 Tanks in _async_setup statt _async_update_data

Tanks aendern sich selten (Volumen, Name). Nur `_latest_fill` und `_ha_sensors` muessen pro Poll aktualisiert werden. Tank-Stammdaten in `_async_setup` laden, nur Fill-Status pollen.

---

## 5. RunCoordinator: Gleiche Optimierungen

Analog zu PlantCoordinator:
- `_async_setup()` fuer Fertilizer-Lookup
- `asyncio.gather()` fuer paralleles Enrichment
- `always_update=False`
- `async_timeout.timeout(30)`

---

## 6. AlertCoordinator und TaskCoordinator

Diese sind bereits schlank (jeweils 1 API-Call). Anpassungen:
- `config_entry=entry` Parameter
- `always_update=False`
- `async_timeout.timeout(10)` (kuerzerer Timeout fuer simple Calls)

---

## 7. PARALLEL_UPDATES auf Plattformen

### 7.1 Konstante pro Plattform-Datei

```python
# sensor.py
PARALLEL_UPDATES = 0  # CoordinatorEntity — kein eigenes Polling

# binary_sensor.py
PARALLEL_UPDATES = 0

# button.py
PARALLEL_UPDATES = 1  # Serialisiere Button-Presses

# calendar.py
PARALLEL_UPDATES = 0

# todo.py
PARALLEL_UPDATES = 1  # Serialisiere Task-Completions
```

`0` = Coordinator-managed (kein eigenes Polling).
`1` = Serialisiere Schreib-Operationen (Button-Press, Task-Complete).

---

## 8. Backend-Empfehlung: Bulk-Endpoints

Um die API-Call-Anzahl fundamental zu reduzieren, sollten folgende Bulk-Endpoints im Backend ergaenzt werden:

| Endpoint | Beschreibung | Ersetzt |
|----------|-------------|---------|
| `GET /api/v1/t/{slug}/plant-instances?enriched=true` | Pflanzen mit Nutrient Plan, Dosages, Phase History | 4N+1 Calls → 1 Call |
| `GET /api/v1/t/{slug}/locations?enriched=true` | Locations mit Runs, Tanks, Plans, Timelines | Dutzende Calls → 1 Call |
| `GET /api/v1/t/{slug}/planting-runs?enriched=true` | Runs mit Plan, Entries, Timeline, Channels | 4N+1 Calls → 1 Call |

**Hinweis:** Diese Backend-Endpoints sind eine Empfehlung, kein Blocker fuer die Coordinator-Optimierung. Die parallele Enrichment-Strategie (Option B) funktioniert auch ohne Backend-Aenderung.

---

## 9. Akzeptanzkriterien

- [ ] Alle 5 Coordinators haben `config_entry=entry` Parameter
- [ ] Alle 5 Coordinators haben `always_update=False`
- [ ] Alle 5 Coordinators haben `async_timeout.timeout()` in `_async_update_data`
- [ ] PlantCoordinator und LocationCoordinator haben `_async_setup()` fuer Stammdaten
- [ ] PlantCoordinator nutzt `asyncio.gather()` fuer paralleles Enrichment
- [ ] Fertilizer-Lookup wird nicht bei jedem Poll neu geladen
- [ ] Tank-Stammdaten werden in `_async_setup()` geladen, nur Fill-Status pollt
- [ ] `PARALLEL_UPDATES` ist auf allen 5 Plattform-Dateien gesetzt
- [ ] API-Calls pro Poll sind dokumentiert (Ziel: <15 bei 10 Pflanzen)
