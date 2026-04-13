# HA-Integrationsanforderungen abgeleitet aus REQ-004: Duenge-Logik

```yaml
Quelle: REQ-004 v3.0 (Multi-Channel Delivery)
Abgeleitet am: 2026-02-28
Abgeleitet von: HA-Integration-Requirements-Engineer (Subagent)
Erweitert: HA-CUSTOM-INTEGRATION.md v1.1
Status: Entwurf
Version: 1.0
Kernfokus: Automatische Mischanlage (Peristaltik-Pumpen via ESPHome/Shelly)
```

## 1. Zusammenfassung

REQ-004 ist fuer die HA-Integration eines der wertvollsten REQs, weil es den **geschlossenen Regelkreis "Berechnung -> Mischung -> Messung -> Feedback"** ermoeglicht. Kamerplanter berechnet praezise Mischrezepte (Dosierungen, Reihenfolge, Ziel-EC/pH, Mischpausen), und Home Assistant steuert die physische Mischanlage (Peristaltik-Pumpen, Magnetventile, EC/pH-Sensoren im Mischtank). Der Feedback-Loop schliesst sich, indem HA die gemessenen EC/pH-Werte nach dem Mischvorgang an KP zurueckmeldet.

Die Integration folgt dem **Sollwert-Modell (Modus B)**: Kamerplanter berechnet und publiziert Dosierungen als Sensor-Entities, HA-Automationen steuern die Pumpen eigenstaendig. Modus B wird empfohlen, weil:
- Die Pumpensteuerung hardware-nah und latenz-sensitiv ist (ESPHome lokal, kein Cloud-Roundtrip)
- Grower die Mischsequenz in ihrer HA-Automation anpassen koennen (Pumpen-Kalibrierung, Wartezeiten)
- Bei KP-Ausfall kann HA mit den letzten bekannten Sollwerten weiterarbeiten (RestoreEntity)

| Integrationsrichtung | Relevanz | Neue Entities | Neue Endpoints | Neue Events |
|---------------------|----------|---------------|----------------|-------------|
| Seite A (KP->HA) | **Hoch** | 16 | 3 | 2 |
| Seite B (HA->KP) | **Hoch** | -- | 2 | 1 |
| Seite C (KP->Aktoren) | **Hoch** | 3 | -- | -- |

---

## 2. Entity-Spezifikation

### 2.1 Neue Sensor-Entities (Seite A: KP->HA Export)

| # | Entity-ID-Pattern | Quelle (API/Berechnung) | Typ | Einheit | device_class | state_class | Coordinator | Polling |
|---|-------------------|------------------------|-----|---------|-------------|-------------|-------------|---------|
| E-004-001 | `sensor.kp_{plant}_target_ec` | `GET .../current-dosages` | sensor | mS/cm | -- | measurement | NutrientCoordinator | 300s |
| E-004-002 | `sensor.kp_{plant}_target_ph` | `GET .../current-dosages` | sensor | pH | -- | measurement | NutrientCoordinator | 300s |
| E-004-003 | `sensor.kp_{plant}_mixing_recipe` | `GET .../current-dosages` | sensor | -- | -- | -- | NutrientCoordinator | 300s |
| E-004-004 | `sensor.kp_{run}_next_watering` | `GET .../mixing-summary` | sensor | -- | timestamp | -- | NutrientCoordinator | 300s |
| E-004-005 | `sensor.kp_{run}_mixing_recipe` | `GET .../mixing-summary` | sensor | -- | -- | -- | NutrientCoordinator | 300s |
| E-004-006 | `sensor.kp_{fert}_stock_ml` | `GET .../fertilizers/` | sensor | mL | -- | measurement | FertilizerStockCoordinator | 600s |
| E-004-007 | `sensor.kp_{fert}_stock_weeks` | Berechnet aus Stock + avg Dosierung | sensor | -- | -- | -- | FertilizerStockCoordinator | 600s |
| E-004-008 | `sensor.kp_{run}_plan_name` | `GET .../mixing-summary` | sensor | -- | -- | -- | NutrientCoordinator | 300s |
| E-004-009 | `sensor.kp_{run}_current_phase_ec` | `GET .../mixing-summary` | sensor | mS/cm | -- | measurement | NutrientCoordinator | 300s |
| E-004-010 | `sensor.kp_{run}_current_phase_ph` | `GET .../mixing-summary` | sensor | pH | -- | measurement | NutrientCoordinator | 300s |

#### E-004-001: Target EC (Pflanze)

**Beschreibung:** Ziel-EC fuer die aktuelle Wachstumsphase der Pflanze, abgeleitet aus dem zugewiesenen NutrientPlan. Dieser Wert ist der primaere Sollwert fuer die Mischanlage.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/plants/{key}/current-dosages`
- Response-Feld: `response.target_ec_ms`
- Fallback: `unavailable` wenn kein NutrientPlan zugewiesen

**Entity-Attribute (extras):**
```python
{
    "plan_name": "Tomato Heavy Coco",        # Name des zugewiesenen Plans
    "current_phase": "flowering",             # Aktuelle Wachstumsphase
    "week_in_phase": 3,                       # Woche innerhalb der Phase
    "base_water_ec": 0.2,                     # Falls bekannt (aus letztem FeedingEvent)
    "ec_budget": 1.6,                         # target_ec - base_water_ec
}
```

**HA-Nutzung:**
- Dashboard: Gauge-Card (0-4.0 mS, Farbzonen: gruen 0.8-2.0, gelb >2.0, rot >3.0)
- Automation-Trigger: Aenderung bei Phasenwechsel oder Plan-Wechsel

---

#### E-004-002: Target pH (Pflanze)

**Beschreibung:** Ziel-pH fuer die aktuelle Wachstumsphase. Steuergroesse fuer die pH-Down/pH-Up-Pumpe der Mischanlage.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/plants/{key}/current-dosages`
- Response-Feld: `response.target_ph`

**Entity-Attribute (extras):**
```python
{
    "ph_tolerance": 0.3,                      # Akzeptable Abweichung
    "current_phase": "flowering",
}
```

**HA-Nutzung:**
- Dashboard: Gauge-Card (4.0-8.0, Farbzonen: gruen 5.5-6.5, gelb <5.5 oder >6.5)
- Automation: pH-Down/pH-Up-Pumpe bis Ziel-pH +/- Toleranz

---

#### E-004-003: Mixing Recipe (Pflanze)

**Beschreibung:** Vollstaendiges Mischrezept fuer die aktuelle Phase als strukturiertes Attribut-Objekt. Der `state`-Wert ist die Anzahl der Duenger im Rezept (z.B. `"4"` fuer 4-Komponenten-Rezept). Die eigentlichen Dosierungen werden als Entity-Attribute exponiert.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/plants/{key}/current-dosages`
- Response-Felder: `response.dosages[]` (Array sortiert nach `mixing_priority`)

**Entity-Attribute (extras):**
```python
{
    "dosage_count": 4,
    # Dosierungen als nummerierte Attribute (sortiert nach mixing_priority):
    "dosage_1_product": "CalMag",
    "dosage_1_ml_per_liter": 1.5,
    "dosage_1_priority": 3,
    "dosage_1_optional": False,
    "dosage_2_product": "FloraMicro",
    "dosage_2_ml_per_liter": 2.0,
    "dosage_2_priority": 4,
    "dosage_2_optional": False,
    "dosage_3_product": "FloraGro",
    "dosage_3_ml_per_liter": 2.0,
    "dosage_3_priority": 5,
    "dosage_3_optional": False,
    "dosage_4_product": "PK 13-14",
    "dosage_4_ml_per_liter": 0.5,
    "dosage_4_priority": 6,
    "dosage_4_optional": True,
    # Mischhinweise als JSON-String (fuer Template-Rendering)
    "mixing_instructions_json": "[\"CalMag zuerst\",\"30s ruehren\",...]",
    "feeding_frequency_per_week": 3,
    "volume_per_feeding_liters": 5.0,
}
```

**HA-Nutzung:**
- Dashboard: Markdown-Card mit Jinja-Template das `dosage_N_*`-Attribute iteriert
- Automation: `dosage_N_ml_per_liter` * Tank-Volumen = absolute Dosierung fuer Pumpe N

**Hinweis:** Die nummerierten `dosage_N_*`-Attribute sind notwendig, weil HA-Entity-Attribute keine verschachtelten Arrays unterstuetzen. Maximal 10 Dosierungen (dosage_1 bis dosage_10).

---

#### E-004-004: Naechster Giesstermin (PlantingRun)

**Beschreibung:** Naechster geplanter Giesstermin fuer den PlantingRun, abgeleitet aus dem WateringSchedule des zugewiesenen NutrientPlans. Bezieht sich auf den Run (nicht die einzelne Pflanze), da Bewaesserung typisch auf Run-Ebene erfolgt.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/planting-runs/{key}/mixing-summary` (NEU, siehe API-004-001)
- Response-Feld: `response.next_watering_date`, `response.next_watering_time`

**Entity-Attribute (extras):**
```python
{
    "next_date": "2026-03-01",
    "next_time": "08:00",
    "schedule_mode": "weekdays",               # "weekdays" oder "interval"
    "weekday_schedule": "Mo,Mi,Fr",            # Menschenlesbare Tage
    "interval_days": None,                     # Nur bei mode=interval
    "reminder_hours_before": 2,
    "application_method": "drench",
    "last_watering_date": "2026-02-27",
}
```

**HA-Nutzung:**
- Dashboard: Entities-Card mit "naechster Giesstermin" als Zeitstempel
- Automation-Trigger: `platform: time` auf `next_time` am `next_date` -> Mischanlage starten

---

#### E-004-005: Mixing Recipe (PlantingRun-Ebene)

**Beschreibung:** Aggregiertes Mischrezept fuer den gesamten PlantingRun. Da alle Pflanzen im Run denselben NutrientPlan folgen, ist das Rezept identisch. Dieses Entity ist der **primaere Datenpunkt fuer die Mischanlage**, da die Mischanlage typisch einen gesamten Tank fuer den Run mischt, nicht pro Pflanze.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/planting-runs/{key}/mixing-summary` (NEU)
- Response-Feld: `response.dosages[]`, `response.target_ec_ms`, `response.target_ph`

**Entity-Attribute (extras):**
```python
{
    "run_name": "Tomato Run 2026-Q1",
    "plan_name": "Tomato Heavy Coco",
    "current_phase": "flowering",
    "target_ec_ms": 1.8,
    "target_ph": 6.0,
    "tank_volume_liters": 50.0,                # Falls Tank zugewiesen (REQ-014)
    "dosage_count": 4,
    # Dosierungen (gleiche nummerierte Struktur wie E-004-003)
    "dosage_1_product": "CalMag",
    "dosage_1_ml_per_liter": 1.5,
    "dosage_1_total_ml": 75.0,                 # ml_per_liter * tank_volume
    "dosage_1_priority": 3,
    "dosage_1_wait_minutes": 2,                # Mischpause aus MixingInstruction
    "dosage_2_product": "FloraMicro",
    "dosage_2_ml_per_liter": 2.0,
    "dosage_2_total_ml": 100.0,
    "dosage_2_priority": 4,
    "dosage_2_wait_minutes": 1,
    # ... weitere Dosierungen
    "ph_adjustment_needed": True,
    "ph_adjustment_type": "pH Down",
    "ph_adjustment_estimated_ml": 3.5,
    # Flushing-Status
    "flushing_active": False,
    "flushing_day": None,
    "flushing_total_days": None,
}
```

**HA-Nutzung:**
- Dashboard: Detaillierte Mischrezept-Card
- Automation: `dosage_N_total_ml` direkt als Pumpenlaufzeit berechenbar (ml / Pumpen-Flow-Rate)

---

#### E-004-006: Fertilizer Stock (ml verbleibend)

**Beschreibung:** Aktueller Bestand eines Duengers in Millilitern. Pro Duenger mit FertilizerStock-Eintrag eine Entity.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/fertilizers/` (erweitert um Stock-Daten)
- Response-Feld: `response[].stock.current_volume_ml`

**Entity-Attribute (extras):**
```python
{
    "product_name": "FloraGro",
    "brand": "General Hydroponics",
    "expiry_date": "2027-06-15",
    "days_until_expiry": 472,
    "batch_number": "FG-2026-001",
    "cost_per_liter": 12.50,
}
```

**HA-Nutzung:**
- Dashboard: Gauge-Card (Fuellstand)
- Automation-Trigger: `below: 500` -> Nachbestell-Warnung

---

#### E-004-007: Fertilizer Stock (geschaetzte Wochen verbleibend)

**Beschreibung:** Geschaetzte Anzahl Wochen bis der Duengervorrat aufgebraucht ist, basierend auf dem durchschnittlichen Verbrauch der letzten 4 Wochen.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/fertilizers/{key}/stock-forecast` (NEU, siehe API-004-002)
- Response-Feld: `response.weeks_remaining`

**Entity-Attribute (extras):**
```python
{
    "product_name": "FloraGro",
    "current_volume_ml": 750.0,
    "avg_weekly_consumption_ml": 180.0,
    "weeks_remaining": 4.2,
    "reorder_threshold_weeks": 2,              # Konfigurierbar
    "reorder_needed": False,
}
```

**HA-Nutzung:**
- Dashboard: Entities-Card mit `weeks_remaining`
- Automation-Trigger: `below: 2` -> Nachbestell-Alert

---

### 2.2 Neue Binary-Sensor-Entities

| # | Entity-ID-Pattern | Quelle | Typ | device_class | Coordinator | Polling |
|---|-------------------|--------|-----|-------------|-------------|---------|
| E-004-011 | `binary_sensor.kp_{run}_flushing_active` | `GET .../mixing-summary` | binary_sensor | -- | NutrientCoordinator | 300s |
| E-004-012 | `binary_sensor.kp_{fert}_reorder_needed` | `GET .../stock-forecast` | binary_sensor | problem | FertilizerStockCoordinator | 600s |
| E-004-013 | `binary_sensor.kp_{fert}_expired` | `GET .../fertilizers/` | binary_sensor | problem | FertilizerStockCoordinator | 600s |
| E-004-014 | `binary_sensor.kp_{run}_watering_due_today` | `GET .../mixing-summary` | binary_sensor | -- | NutrientCoordinator | 300s |

#### E-004-011: Flushing Active (PlantingRun)

**Beschreibung:** `on` wenn der PlantingRun sich aktuell in der Flushing-Phase befindet (letzten N Tage vor Ernte, nur Wasser statt Naehrloesung). Kritisch fuer die Mischanlage: Bei Flushing duerfen **keine Duenger** dosiert werden.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/planting-runs/{key}/mixing-summary` (NEU)
- Response-Feld: `response.flushing_active`
- Logik: `true` wenn Phase-Entry phase_name = `'harvest'` UND `target_ec_ms = 0.0`

**Entity-Attribute (extras):**
```python
{
    "flushing_day": 7,                         # Tag X des Flushing-Protokolls
    "flushing_total_days": 14,                 # Gesamtdauer
    "target_ec": 0.0,                          # Sollte 0 sein waehrend Flush
    "substrate_type": "coco",
}
```

**HA-Nutzung:**
- Automation: Wenn `on` -> Mischanlage pumpt nur pH-korrigiertes Wasser, keine Duenger
- Dashboard: Alert-Badge "FLUSHING" auf Run-Card

---

#### E-004-012: Reorder Needed (Duenger)

**Beschreibung:** `on` wenn der geschaetzte Vorrat unter den Nachbestell-Schwellwert (default: 2 Wochen) faellt.

**Datenquelle:**
- Berechnet aus E-004-007 `weeks_remaining < reorder_threshold_weeks`

**HA-Nutzung:**
- Dashboard: Problem-Badge
- Automation: -> Nachbestell-Notification

---

#### E-004-014: Watering Due Today (PlantingRun)

**Beschreibung:** `on` wenn der PlantingRun heute gemaess WateringSchedule gegossen werden soll. Direkter Trigger fuer die Mischanlage.

**Datenquelle:**
- API-Endpoint: `GET /api/v1/t/{slug}/planting-runs/{key}/mixing-summary` (NEU)
- Response-Feld: `response.watering_due_today`
- Logik: `WateringScheduleEngine.is_watering_due(schedule, today, last_watering_date)`

**Entity-Attribute (extras):**
```python
{
    "preferred_time": "08:00",
    "last_watering_date": "2026-02-26",
    "application_method": "drench",
}
```

**HA-Nutzung:**
- Automation-Trigger: `to: "on"` -> Mischanlage starten zum `preferred_time`

---

### 2.3 Neue Button-Entities (Seite C: Steuerung)

| # | Entity-ID-Pattern | Aktion | Icon | Coordinator |
|---|-------------------|--------|------|-------------|
| E-004-015 | `button.kp_{run}_confirm_feeding` | FeedingEvent per API erstellen | `mdi:check-circle` | -- |
| E-004-016 | `button.kp_{run}_start_flushing` | Flushing-Protokoll starten | `mdi:water-off` | -- |

#### E-004-015: Confirm Feeding (Button)

**Beschreibung:** Erstellt ein FeedingEvent ueber die KP-API als Bestaetigung, dass die Mischanlage den Mischvorgang abgeschlossen hat und die Naehrloesung ausgebracht wurde. Wird typisch am Ende einer HA-Misch-Automation aufgerufen.

**Implementierung:**
```python
class KpConfirmFeedingButton(ButtonEntity):
    _attr_icon = "mdi:check-circle"

    async def async_press(self) -> None:
        # Messwerte aus HA-Sensoren lesen (EC/pH im Mischtank)
        tank_ec = self.hass.states.get(self._tank_ec_entity_id)
        tank_ph = self.hass.states.get(self._tank_ph_entity_id)

        # FeedingEvent an KP senden
        await self.api.post(
            f"/api/v1/t/{self._slug}/watering-events/confirm",
            json={
                "run_key": self._run_key,
                "task_key": self._task_key,  # Falls Task existiert
                "measured_ec": float(tank_ec.state) if tank_ec else None,
                "measured_ph": float(tank_ph.state) if tank_ph else None,
                "volume_liters": self._tank_volume,
            }
        )
        # Sofortige UI-Aktualisierung (HA-NFR-003)
        self.async_write_ha_state()
        # Coordinator refresh fuer abhaengige Entities
        await self.coordinator.async_request_refresh()
```

**HA-Nutzung:**
- Am Ende einer Misch-Automation: `button.press` -> FeedingEvent in KP dokumentiert
- Service-Call aus Automation: `button.press` mit `entity_id: button.kp_run001_confirm_feeding`

---

## 3. API-Anforderungen an Kamerplanter-Backend

### 3.1 Bestehende Endpoints (ausreichend)

| Endpoint | Liefert Daten fuer | Status |
|----------|-------------------|--------|
| `GET /api/v1/t/{slug}/plants/{key}/current-dosages` | E-004-001, E-004-002, E-004-003 | Implementiert |
| `GET /api/v1/t/{slug}/fertilizers/` | E-004-006 (teilweise) | Implementiert (Stock-Daten muessen erweitert werden) |
| `POST /api/v1/t/{slug}/watering-events/confirm` | E-004-015 (Feedback) | Implementiert |
| `POST /api/v1/t/{slug}/watering-events/quick-confirm` | E-004-015 (vereinfacht) | Implementiert |
| `POST /api/v1/t/{slug}/feeding-events` | Manuelles FeedingEvent | Implementiert |
| `POST /api/v1/t/{slug}/nutrient-calculations/mixing-protocol` | Einmal-Berechnung | Implementiert |
| `POST /api/v1/t/{slug}/nutrient-calculations/flushing` | Flushing-Schedule | Implementiert |

### 3.2 Fehlende/Erweiterte Endpoints

| # | Methode | Pfad | Request | Response | Benoetigt fuer |
|---|---------|------|---------|----------|---------------|
| API-004-001 | GET | `/api/v1/t/{slug}/planting-runs/{key}/mixing-summary` | -- | `MixingSummaryResponse` | E-004-004, E-004-005, E-004-009, E-004-010, E-004-011, E-004-014 |
| API-004-002 | GET | `/api/v1/t/{slug}/fertilizers/{key}/stock-forecast` | -- | `StockForecastResponse` | E-004-007, E-004-012 |
| API-004-003 | POST | `/api/v1/t/{slug}/planting-runs/{key}/mixing-feedback` | `MixingFeedbackRequest` | `MixingFeedbackResponse` | Seite B: HA->KP Messwert-Feedback |

---

#### API-004-001: Mixing Summary (PlantingRun)

**Zweck:** Zentraler Endpoint fuer den NutrientCoordinator. Liefert alle Informationen, die die Mischanlage fuer einen PlantingRun braucht, in einem einzigen Request. Vermeidet N+1-Requests fuer Pflanzen, Plan, Phase-Entry, Dosierungen und Schedule.

**HTTP:** `GET /api/v1/t/{slug}/planting-runs/{key}/mixing-summary`

**Auth:** JWT Bearer Token, Tenant-Mitgliedschaft (Viewer-Rolle ausreichend)

**Response-Schema (MixingSummaryResponse):**
```python
class MixingSummaryResponse(BaseModel):
    run_key: str
    run_name: str
    plan_key: Optional[str]                    # null wenn kein Plan zugewiesen
    plan_name: Optional[str]
    current_phase: Optional[str]               # Dominante Phase der Pflanzen im Run
    plant_count: int                           # Anzahl aktiver Pflanzen im Run

    # Zielwerte fuer aktuelle Phase
    target_ec_ms: Optional[float]
    target_ph: Optional[float]
    npk_ratio: Optional[tuple[float, float, float]]

    # Dosierungen (sortiert nach mixing_priority)
    dosages: list[DosageSummary]

    # Giesstermin-Informationen
    watering_due_today: bool
    next_watering_date: Optional[str]          # ISO 8601 date
    next_watering_time: Optional[str]          # HH:MM
    schedule_mode: Optional[str]               # "weekdays" | "interval"
    last_watering_date: Optional[str]          # ISO 8601 date

    # Flushing-Status
    flushing_active: bool
    flushing_day: Optional[int]                # Tag X des Flushing-Protokolls
    flushing_total_days: Optional[int]

    # Multi-Channel (wenn Channels vorhanden)
    active_channels: list[ChannelSummary]

class DosageSummary(BaseModel):
    fertilizer_key: str
    product_name: str
    brand: str
    ml_per_liter: float
    mixing_priority: int
    optional: bool
    tank_safe: bool
    wait_minutes_after: Optional[int]          # Mischpause nach Zugabe (aus MixingInstruction)

class ChannelSummary(BaseModel):
    channel_id: str
    label: str
    application_method: str                    # fertigation|drench|foliar|top_dress
    enabled: bool
    due_today: bool
    target_ec_ms: Optional[float]              # Channel-Level Override oder Phase-Level
    target_ph: Optional[float]
    dosages: list[DosageSummary]
```

**Backend-Implementierung (Pseudo-Code):**
```python
@router.get("/{key}/mixing-summary")
def get_mixing_summary(
    key: str,
    plan_service: NutrientPlanService = Depends(...),
    run_service: PlantingRunService = Depends(...),
    watering_engine: WateringScheduleEngine = Depends(...),
):
    run = run_service.get_run(key)
    plan = plan_service.get_run_plan(key)  # via RUN_FOLLOWS_PLAN edge
    if not plan:
        return MixingSummaryResponse(run_key=key, run_name=run.name, ...)

    # Dominante Phase der Pflanzen ermitteln
    plants_by_phase = run_service.get_plants_by_phase(key)
    dominant_phase = max(plants_by_phase, key=lambda p: len(plants_by_phase[p]))

    # Phase-Entry fuer dominante Phase
    entry = next((e for e in plan.phase_entries if e.phase_name == dominant_phase), None)

    # Naechster Giesstermin
    schedule = plan.watering_schedule
    next_dates = watering_engine.get_next_watering_dates(schedule, today, 14, last_watering)
    watering_due = watering_engine.is_watering_due(schedule, today, last_watering)

    # Flushing-Status
    flushing_active = entry and entry.phase_name == 'harvest' and entry.target_ec_ms == 0.0

    # Multi-Channel
    channels = get_effective_channels(entry) if entry else []

    return MixingSummaryResponse(...)
```

---

#### API-004-002: Stock Forecast (Duenger)

**Zweck:** Geschaetzte Restlaufzeit eines Duengervorrats basierend auf dem durchschnittlichen Verbrauch der letzten 4 Wochen.

**HTTP:** `GET /api/v1/t/{slug}/fertilizers/{key}/stock-forecast`

**Response-Schema:**
```python
class StockForecastResponse(BaseModel):
    fertilizer_key: str
    product_name: str
    current_volume_ml: float
    avg_weekly_consumption_ml: float            # Durchschnitt der letzten 4 Wochen
    weeks_remaining: Optional[float]            # null wenn kein Verbrauch gemessen
    reorder_needed: bool                        # weeks_remaining < 2
    expiry_date: Optional[str]                  # ISO 8601 date
    days_until_expiry: Optional[int]
```

**Backend-Logik:**
```python
# Durchschnittlicher Verbrauch: Summe aller FeedingEvents der letzten 28 Tage
# gruppiert nach Fertilizer, geteilt durch 4 (Wochen)
avg_consumption = sum(
    fe.fertilizers_used[fert_key].ml_applied
    for fe in feeding_events_last_28_days
) / 4.0
weeks_remaining = stock.current_volume_ml / avg_consumption if avg_consumption > 0 else None
```

---

#### API-004-003: Mixing Feedback (HA->KP)

**Zweck:** Endpoint fuer die Mischanlage, um die **gemessenen EC/pH-Werte nach dem Mischvorgang** an Kamerplanter zurueckzumelden. Unterscheidet sich von `watering-events/confirm` dadurch, dass es sich um eine **Tank-Messung** handelt (Loesung im Mischtank), nicht um eine Substrat-Messung.

**HTTP:** `POST /api/v1/t/{slug}/planting-runs/{key}/mixing-feedback`

**Request-Schema:**
```python
class MixingFeedbackRequest(BaseModel):
    measured_ec_ms: float = Field(ge=0, le=10.0)
    measured_ph: float = Field(ge=0, le=14.0)
    water_temperature_c: Optional[float] = Field(None, ge=0, le=50)
    tank_volume_liters: float = Field(gt=0)
    mixing_timestamp: Optional[str] = None     # ISO 8601, default: now()
    source: str = "home_assistant"              # Provenance-Tracking
    channel_id: Optional[str] = None           # Bei Multi-Channel: welcher Channel
    notes: Optional[str] = Field(None, max_length=500)
```

**Response-Schema:**
```python
class MixingFeedbackResponse(BaseModel):
    status: str                                # "ok" | "ec_deviation" | "ph_deviation"
    target_ec_ms: float
    measured_ec_ms: float
    ec_deviation: float                        # abs(target - measured)
    target_ph: float
    measured_ph: float
    ph_deviation: float
    warnings: list[str]                        # z.B. ["EC 0.4 mS ueber Ziel"]
    feeding_event_key: Optional[str]           # Falls automatisch FeedingEvent erstellt
```

**Backend-Logik:**
```python
# 1. Deviation pruefen
ec_dev = abs(target_ec - request.measured_ec_ms)
ph_dev = abs(target_ph - request.measured_ph)

warnings = []
if ec_dev > 0.3:
    warnings.append(f"EC-Abweichung {ec_dev:.2f} mS — Dosierungen pruefen")
if ph_dev > 0.5:
    warnings.append(f"pH-Abweichung {ph_dev:.2f} — pH-Korrektur nachdosieren")

# 2. Optional: TankState aktualisieren (REQ-014)
if tank_key:
    tank_service.update_state(tank_key, ec=request.measured_ec_ms, ph=request.measured_ph)

# 3. Feedback fuer RunoffAnalyzer-Integration speichern
```

---

### 3.3 Event-Publishing (MQTT)

| # | Topic-Pattern | Payload-Schema | Trigger | Latenz-Anforderung |
|---|---------------|---------------|---------|-------------------|
| EVT-004-001 | `kamerplanter/{tenant}/events/plan-changed` | `{run_key, plan_key, plan_name, phase, target_ec, target_ph}` | NutrientPlan-Zuweisung/Wechsel, Phasenwechsel | <30s |
| EVT-004-002 | `kamerplanter/{tenant}/events/flushing-started` | `{run_key, flush_days, substrate_type}` | Phasenwechsel zu `harvest` mit EC=0 | <30s |

#### EVT-004-001: Plan Changed

**Beschreibung:** Wird gefeuert wenn sich das Mischrezept fuer einen Run aendert. Trigger fuer HA: Mischanlage muss mit neuen Dosierungen arbeiten.

**Trigger-Bedingungen:**
- NutrientPlan wird einem Run zugewiesen (`POST .../planting-runs/{key}/nutrient-plan`)
- NutrientPlan wird geaendert (`PUT .../nutrient-plans/{key}`)
- Pflanze wechselt Phase (`PhaseTransitionEngine.transition_to_phase()`)
- Phase-Entry-Dosierungen werden geaendert

**HA-Reaktion:**
- NutrientCoordinator forciert sofortiges Re-Polling (`async_request_refresh()`)
- Optional: MQTT-Listener statt Polling (zukuenftiges Upgrade, siehe HA-CUSTOM-INTEGRATION.md Hinweis zu MQTT)

#### EVT-004-002: Flushing Started

**Beschreibung:** Wird gefeuert wenn das Flushing-Protokoll startet. Kritisches Signal fuer die Mischanlage: Ab sofort nur Wasser, keine Duenger.

**HA-Reaktion:**
- Mischanlage schaltet alle Duenger-Pumpen ab
- Nur Frischwasser-Ventil + pH-Korrektur aktiv

---

## 4. Coordinator-Erweiterungen

### 4.1 Neuer Coordinator: NutrientCoordinator

**Begruendung:** Die Naehrstoff-Entities (Mischrezept, Ziel-EC/pH, Giesstermin, Flushing) haben ein anderes Aktualisierungsverhalten als die bestehenden Plant- und Tank-Coordinators. Mischrezepte aendern sich selten (bei Phasenwechsel, Plan-Aenderung), muessen aber zuverlaessig abgerufen werden. Ein eigener Coordinator erlaubt:
- Gezieltes Polling-Intervall (300s Standard, reduzierbar auf 60s fuer aktive Mischvorgaenge)
- Separate Fehlerbehandlung (NutrientPlan nicht zugewiesen != API-Fehler)
- Eigene RestoreEntity-Logik (letztes bekanntes Mischrezept bei KP-Ausfall)

| Coordinator | Polling-Intervall | API-Endpoint | Entities |
|-------------|-------------------|-------------|----------|
| `NutrientCoordinator` | 300s (5 min) | `GET /api/v1/t/{slug}/planting-runs/{key}/mixing-summary` | E-004-004 bis E-004-005, E-004-008 bis E-004-010, E-004-011, E-004-014 |

**Pro PlantingRun** wird ein separater Coordinator-Aufruf gemacht (nicht pro Pflanze). Bei 3 Runs = 3 API-Requests alle 300s.

**Implementierung:**
```python
class NutrientCoordinator(DataUpdateCoordinator):
    """Coordinator fuer Naehrstoff-/Mischrezept-Daten pro PlantingRun."""

    def __init__(self, hass, entry, api, run_key: str, slug: str):
        super().__init__(
            hass, LOGGER,
            name=f"kp_nutrient_{run_key}",
            update_interval=timedelta(seconds=300),
        )
        self._api = api
        self._run_key = run_key
        self._slug = slug

    async def _async_update_data(self) -> dict:
        try:
            return await self._api.get(
                f"/api/v1/t/{self._slug}/planting-runs/{self._run_key}/mixing-summary"
            )
        except ConnectionError:
            raise UpdateFailed("Kamerplanter nicht erreichbar")
        except AuthenticationError:
            raise ConfigEntryAuthFailed("API-Key ungueltig")
```

### 4.2 Neuer Coordinator: FertilizerStockCoordinator

| Coordinator | Polling-Intervall | API-Endpoint | Entities |
|-------------|-------------------|-------------|----------|
| `FertilizerStockCoordinator` | 600s (10 min) | `GET /api/v1/t/{slug}/fertilizers/` + `GET .../stock-forecast` | E-004-006, E-004-007, E-004-012, E-004-013 |

**Begruendung:** Duengerbestaende aendern sich langsam (nach jeder Duengung). 10-Minuten-Polling reicht aus. Separater Coordinator, weil die Datenquelle (Fertilizer-Collection) unabhaengig von Runs/Pflanzen ist.

---

## 5. Steuerungsanforderungen (Seite C)

### 5.1 Steuerungsmatrix

Die Mischanlage ist der **zentrale Aktor** fuer REQ-004. Die Steuerungsgrenze ist klar: **Kamerplanter berechnet, Home Assistant mischt.**

| KP-Aktion | HA-Aktion | Modus A (KP steuert) | Modus B (HA regelt) | Fail-Safe |
|-----------|-----------|----------------------|--------------------|-----------|
| Dosierungen berechnen | Pumpen ansteuern | KP sendet Service-Calls an HA (NICHT empfohlen) | KP publiziert Sollwerte als Entities, HA-Automation steuert Pumpen | Pumpen AUS, Alert |
| Ziel-EC/pH setzen | EC/pH messen + korrigieren | KP wartet auf Messwert, dosiert nach | HA misst EC/pH im Tank, dosiert pH-Down nach, meldet Ergebnis | Letzte bekannte Werte |
| Flushing aktivieren | Duenger-Pumpen deaktivieren | KP deaktiviert Pumpen via Service-Call | HA reagiert auf `binary_sensor.kp_{run}_flushing_active` = on | Nur Wasser (sicher) |
| Giesstermin signalisieren | Mischvorgang starten | KP triggert Automation | HA triggert auf `binary_sensor.kp_{run}_watering_due_today` + Uhrzeit | Kein Giessen (sicher) |

**Empfehlung: Modus B (Sollwert-Modell)** aus folgenden Gruenden:

1. **Latenz:** Peristaltik-Pumpen brauchen Echtzeit-Steuerung. ESPHome lauft lokal, KP-API hat Netzwerk-Latenz
2. **Zuverlaessigkeit:** Bei KP-Ausfall arbeitet HA mit letzten bekannten Sollwerten weiter (RestoreEntity)
3. **Flexibilitaet:** Grower koennen die Pump-Sequenz in HA anpassen (Kalibrierung, Wartezeiten)
4. **Einfachheit:** Keine bidirektionale Echtzeit-Kommunikation noetig

### 5.2 Sollwert-Entities (Modus B)

| Entity-ID-Pattern | Beschreibung | Einheit | Aenderungstrigger |
|-------------------|-------------|---------|-------------------|
| `sensor.kp_{run}_target_ec` (= E-004-009) | Ziel-EC fuer Mischanlage | mS/cm | Phasenwechsel, Plan-Aenderung |
| `sensor.kp_{run}_target_ph` (= E-004-010) | Ziel-pH fuer pH-Pumpe | pH | Phasenwechsel, Plan-Aenderung |
| `sensor.kp_{run}_mixing_recipe` (= E-004-005) | Dosierungen pro Duenger | -- | Phasenwechsel, Plan-Aenderung |
| `binary_sensor.kp_{run}_flushing_active` (= E-004-011) | Flushing-Modus aktiv | -- | Phasenwechsel zu harvest |
| `binary_sensor.kp_{run}_watering_due_today` (= E-004-014) | Giessen heute faellig | -- | Taeglich um Mitternacht |

### 5.3 Referenz-Hardware: Typische Mischanlage

Die folgende Hardware-Konfiguration dient als Referenz fuer die Blueprints und ESPHome-Snippets:

| Komponente | Typ | HA-Entity | Beschreibung |
|-----------|-----|-----------|-------------|
| Pumpe 1 (CalMag) | Peristaltik 12V | `switch.pump_calmag` | ~2.5 ml/s bei 12V |
| Pumpe 2 (Base A) | Peristaltik 12V | `switch.pump_base_a` | ~2.5 ml/s bei 12V |
| Pumpe 3 (Base B) | Peristaltik 12V | `switch.pump_base_b` | ~2.5 ml/s bei 12V |
| Pumpe 4 (Booster) | Peristaltik 12V | `switch.pump_booster` | ~2.5 ml/s bei 12V |
| Pumpe 5 (pH Down) | Peristaltik 12V | `switch.pump_ph_down` | ~1.0 ml/s (langsamer!) |
| Pumpe 6 (pH Up) | Peristaltik 12V | `switch.pump_ph_up` | ~1.0 ml/s |
| EC-Sensor | Atlas Scientific | `sensor.mixing_tank_ec` | Im Mischtank |
| pH-Sensor | Atlas Scientific | `sensor.mixing_tank_ph` | Im Mischtank |
| Wasserventil | Magnetventil 12V | `switch.fresh_water_valve` | Frischwasserzulauf |
| Ruehrwerk | Umwaelzpumpe | `switch.mixing_pump` | Ruehren waehrend/nach Zugabe |
| Steuerung | ESP32 + ESPHome | -- | Steuert Relais fuer Pumpen/Ventile |

**ESPHome-Referenz-Konfiguration (Auszug):**
```yaml
# esphome/mixing-station.yaml
esphome:
  name: mixing-station
  platform: ESP32
  board: esp32dev

# Peristaltik-Pumpen ueber Relais-Board (4-Kanal + 2-Kanal)
switch:
  - platform: gpio
    pin: GPIO16
    name: "Pump CalMag"
    id: pump_calmag
    icon: mdi:water-pump
    # Sicherheit: Max 120s Laufzeit (Watchdog)
    on_turn_on:
      - delay: 120s
      - switch.turn_off: pump_calmag
  - platform: gpio
    pin: GPIO17
    name: "Pump Base A"
    id: pump_base_a
    icon: mdi:water-pump
    on_turn_on:
      - delay: 120s
      - switch.turn_off: pump_base_a
  - platform: gpio
    pin: GPIO18
    name: "Pump Base B"
    id: pump_base_b
    icon: mdi:water-pump
    on_turn_on:
      - delay: 120s
      - switch.turn_off: pump_base_b
  - platform: gpio
    pin: GPIO19
    name: "Pump Booster"
    id: pump_booster
    icon: mdi:water-pump
    on_turn_on:
      - delay: 120s
      - switch.turn_off: pump_booster
  - platform: gpio
    pin: GPIO21
    name: "Pump pH Down"
    id: pump_ph_down
    icon: mdi:flask
    on_turn_on:
      - delay: 60s
      - switch.turn_off: pump_ph_down
  - platform: gpio
    pin: GPIO22
    name: "Pump pH Up"
    id: pump_ph_up
    icon: mdi:flask
    on_turn_on:
      - delay: 60s
      - switch.turn_off: pump_ph_up

  - platform: gpio
    pin: GPIO23
    name: "Fresh Water Valve"
    id: fresh_water_valve
    icon: mdi:valve
  - platform: gpio
    pin: GPIO25
    name: "Mixing Pump"
    id: mixing_pump
    icon: mdi:pump

# EC-Sensor (Atlas Scientific via I2C)
sensor:
  - platform: atlas_scientific
    address: 0x64
    name: "Mixing Tank EC"
    id: mixing_tank_ec
    unit_of_measurement: "mS/cm"
    accuracy_decimals: 2
    update_interval: 10s

  # pH-Sensor (Atlas Scientific via I2C)
  - platform: atlas_scientific
    address: 0x63
    name: "Mixing Tank pH"
    id: mixing_tank_ph
    unit_of_measurement: "pH"
    accuracy_decimals: 2
    update_interval: 10s
```

---

## 6. Automation-Blueprints

### Blueprint 1: KP — Automatisches Mischen nach Plan

**Beschreibung:** Wenn heute ein Giesstermin faellig ist, startet die Mischanlage zum konfigurierten Zeitpunkt die vollstaendige Mischsequenz: Frischwasser einfuellen, Duenger in korrekter Reihenfolge dosieren, ruehren, EC/pH messen, pH korrigieren, Ergebnis an KP melden.

```yaml
alias: "KP: Automatisches Mischen nach Plan"
description: >
  Mischt Naehrloesung gemaess Kamerplanter-Rezept.
  Trigger: Giesstermin faellig + preferred_time erreicht.
  Liest Dosierungen aus sensor.kp_{run}_mixing_recipe.
trigger:
  - platform: time
    at: >
      {{ state_attr('sensor.kp_run001_next_watering', 'next_time') | default('08:00') }}
condition:
  # Nur wenn heute Giesstermin
  - condition: state
    entity_id: binary_sensor.kp_run001_watering_due_today
    state: "on"
  # Nicht im Flushing-Modus (eigener Blueprint)
  - condition: state
    entity_id: binary_sensor.kp_run001_flushing_active
    state: "off"
action:
  # --- Phase 1: Frischwasser einfuellen ---
  - service: switch.turn_on
    target:
      entity_id: switch.fresh_water_valve
  - delay:
      # Tank-Volumen / Durchflussrate = Fuellzeit
      # Beispiel: 50L bei 5L/min = 10 Minuten
      minutes: 10
  - service: switch.turn_off
    target:
      entity_id: switch.fresh_water_valve

  # --- Phase 2: Ruehrwerk einschalten ---
  - service: switch.turn_on
    target:
      entity_id: switch.mixing_pump

  # --- Phase 3: Duenger in Reihenfolge dosieren ---
  # Pumpe 1: CalMag (dosage_1)
  - variables:
      ml_calmag: >
        {{ state_attr('sensor.kp_run001_mixing_recipe', 'dosage_1_total_ml') | float(0) }}
      pump_rate_ml_s: 2.5
      pump_time_s_calmag: "{{ (ml_calmag / pump_rate_ml_s) | round(0) }}"
  - condition: template
    value_template: "{{ ml_calmag > 0 }}"
  - service: switch.turn_on
    target:
      entity_id: switch.pump_calmag
  - delay:
      seconds: "{{ pump_time_s_calmag | int }}"
  - service: switch.turn_off
    target:
      entity_id: switch.pump_calmag
  # Mischpause (wait_minutes aus MixingInstruction)
  - delay:
      minutes: >
        {{ state_attr('sensor.kp_run001_mixing_recipe', 'dosage_1_wait_minutes') | int(2) }}

  # Pumpe 2: Base A (dosage_2) — gleiche Logik
  - variables:
      ml_base_a: >
        {{ state_attr('sensor.kp_run001_mixing_recipe', 'dosage_2_total_ml') | float(0) }}
      pump_time_s_base_a: "{{ (ml_base_a / pump_rate_ml_s) | round(0) }}"
  - condition: template
    value_template: "{{ ml_base_a > 0 }}"
  - service: switch.turn_on
    target:
      entity_id: switch.pump_base_a
  - delay:
      seconds: "{{ pump_time_s_base_a | int }}"
  - service: switch.turn_off
    target:
      entity_id: switch.pump_base_a
  - delay:
      minutes: >
        {{ state_attr('sensor.kp_run001_mixing_recipe', 'dosage_2_wait_minutes') | int(1) }}

  # Pumpe 3: Base B (dosage_3) — gleiche Logik
  - variables:
      ml_base_b: >
        {{ state_attr('sensor.kp_run001_mixing_recipe', 'dosage_3_total_ml') | float(0) }}
      pump_time_s_base_b: "{{ (ml_base_b / pump_rate_ml_s) | round(0) }}"
  - condition: template
    value_template: "{{ ml_base_b > 0 }}"
  - service: switch.turn_on
    target:
      entity_id: switch.pump_base_b
  - delay:
      seconds: "{{ pump_time_s_base_b | int }}"
  - service: switch.turn_off
    target:
      entity_id: switch.pump_base_b
  - delay:
      minutes: >
        {{ state_attr('sensor.kp_run001_mixing_recipe', 'dosage_3_wait_minutes') | int(1) }}

  # --- Phase 4: 60s Ruehren lassen ---
  - delay:
      seconds: 60

  # --- Phase 5: EC/pH messen und pruefen ---
  - variables:
      measured_ec: "{{ states('sensor.mixing_tank_ec') | float(0) }}"
      target_ec: "{{ states('sensor.kp_run001_current_phase_ec') | float(1.0) }}"
      measured_ph: "{{ states('sensor.mixing_tank_ph') | float(7.0) }}"
      target_ph: "{{ states('sensor.kp_run001_current_phase_ph') | float(6.0) }}"

  # --- Phase 6: pH-Korrektur ---
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ measured_ph > (target_ph | float + 0.3) }}"
        sequence:
          # pH zu hoch -> pH Down dosieren (schrittweise, 5ml pro Iteration)
          - repeat:
              while:
                - condition: template
                  value_template: >
                    {{ states('sensor.mixing_tank_ph') | float(7) > (target_ph | float + 0.1) }}
              sequence:
                - service: switch.turn_on
                  target:
                    entity_id: switch.pump_ph_down
                - delay:
                    seconds: 5  # ~5ml bei 1ml/s
                - service: switch.turn_off
                  target:
                    entity_id: switch.pump_ph_down
                - delay:
                    seconds: 30  # Warten bis pH-Sensor reagiert
      - conditions:
          - condition: template
            value_template: "{{ measured_ph < (target_ph | float - 0.3) }}"
        sequence:
          - repeat:
              while:
                - condition: template
                  value_template: >
                    {{ states('sensor.mixing_tank_ph') | float(5) < (target_ph | float - 0.1) }}
              sequence:
                - service: switch.turn_on
                  target:
                    entity_id: switch.pump_ph_up
                - delay:
                    seconds: 5
                - service: switch.turn_off
                  target:
                    entity_id: switch.pump_ph_up
                - delay:
                    seconds: 30

  # --- Phase 7: Ruehrwerk abschalten ---
  - service: switch.turn_off
    target:
      entity_id: switch.mixing_pump

  # --- Phase 8: Ergebnis an KP melden ---
  - service: rest_command.kp_mixing_feedback
    data:
      measured_ec: "{{ states('sensor.mixing_tank_ec') }}"
      measured_ph: "{{ states('sensor.mixing_tank_ph') }}"
      tank_volume: 50.0

  # --- Phase 9: Benachrichtigung ---
  - service: notify.mobile_app_phone
    data:
      title: "Mischanlage fertig"
      message: >
        Run: {{ state_attr('sensor.kp_run001_mixing_recipe', 'run_name') }}
        EC: {{ states('sensor.mixing_tank_ec') }} mS (Ziel: {{ target_ec }})
        pH: {{ states('sensor.mixing_tank_ph') }} (Ziel: {{ target_ph }})
mode: single
```

**Zugehoeriger REST-Command (configuration.yaml):**
```yaml
rest_command:
  kp_mixing_feedback:
    url: "http://kamerplanter:8000/api/v1/t/mein-garten/planting-runs/run001/mixing-feedback"
    method: POST
    headers:
      Authorization: "Bearer kp_xxxxx"
      Content-Type: "application/json"
    payload: >
      {
        "measured_ec_ms": {{ measured_ec }},
        "measured_ph": {{ measured_ph }},
        "tank_volume_liters": {{ tank_volume }},
        "source": "home_assistant"
      }
```

**Voraussetzungen:** E-004-005, E-004-009, E-004-010, E-004-011, E-004-014, API-004-001, API-004-003

---

### Blueprint 2: KP — Flushing-Modus aktivieren

**Beschreibung:** Wenn KP den Flushing-Modus aktiviert (Harvest-Phase, EC-Ziel 0), schaltet die Mischanlage auf Nur-Wasser-Modus um. Keine Duengerpumpen, nur pH-korrigiertes Frischwasser.

```yaml
alias: "KP: Flushing-Modus — nur Wasser"
description: >
  Bei aktivem Flushing pumpt die Mischanlage nur pH-korrigiertes Wasser.
  Alle Duengerpumpen bleiben deaktiviert.
trigger:
  - platform: state
    entity_id: binary_sensor.kp_run001_flushing_active
    to: "on"
condition: []
action:
  - service: notify.mobile_app_phone
    data:
      title: "Flushing gestartet!"
      message: >
        {{ state_attr('binary_sensor.kp_run001_flushing_active', 'run_name') }}:
        Flushing-Protokoll aktiv (Tag
        {{ state_attr('binary_sensor.kp_run001_flushing_active', 'flushing_day') }}/
        {{ state_attr('binary_sensor.kp_run001_flushing_active', 'flushing_total_days') }}).
        Mischanlage dosiert nur noch pH-korrigiertes Wasser.
  # Sicherheit: Alle Duenger-Pumpen explizit ausschalten
  - service: switch.turn_off
    target:
      entity_id:
        - switch.pump_calmag
        - switch.pump_base_a
        - switch.pump_base_b
        - switch.pump_booster
  - service: persistent_notification.create
    data:
      title: "FLUSHING AKTIV"
      message: >
        Duengerpumpen deaktiviert. Nur Wasser + pH-Korrektur.
        Tag {{ state_attr('binary_sensor.kp_run001_flushing_active', 'flushing_day') }}
        von {{ state_attr('binary_sensor.kp_run001_flushing_active', 'flushing_total_days') }}.
mode: single
```

**Voraussetzungen:** E-004-011

---

### Blueprint 3: KP — Nachbestell-Warnung

**Beschreibung:** Wenn ein Duenger unter den Nachbestell-Schwellwert (2 Wochen Restvorrat) faellt, wird eine Benachrichtigung mit Produktdetails gesendet.

```yaml
alias: "KP: Duenger nachbestellen"
description: "Warnung wenn Duengervorrat unter 2 Wochen faellt"
trigger:
  - platform: state
    entity_id: binary_sensor.kp_floragro_reorder_needed
    to: "on"
  - platform: state
    entity_id: binary_sensor.kp_calmag_reorder_needed
    to: "on"
  - platform: state
    entity_id: binary_sensor.kp_floramicro_reorder_needed
    to: "on"
  # ... weitere Duenger nach Bedarf
condition: []
action:
  - service: notify.mobile_app_phone
    data:
      title: "Duenger nachbestellen!"
      message: >
        {{ trigger.to_state.attributes.product_name }}
        ({{ trigger.to_state.attributes.brand }}):
        Nur noch {{ trigger.to_state.attributes.current_volume_ml | round(0) }} ml
        (ca. {{ trigger.to_state.attributes.weeks_remaining | round(1) }} Wochen).
        {% if trigger.to_state.attributes.expiry_date %}
        Verfallsdatum: {{ trigger.to_state.attributes.expiry_date }}
        {% endif %}
  - service: persistent_notification.create
    data:
      title: "Duenger-Nachbestellung"
      message: >
        {{ trigger.to_state.attributes.product_name }}: {{ trigger.to_state.attributes.weeks_remaining | round(1) }} Wochen Restvorrat.
mode: queued
max: 10
```

**Voraussetzungen:** E-004-007, E-004-012

---

### Blueprint 4: KP — EC/pH-Messung zurueckmelden

**Beschreibung:** Nach Abschluss eines manuellen oder automatischen Mischvorgangs meldet HA die gemessenen EC/pH-Werte aus dem Mischtank an Kamerplanter zurueck. Kann als eigenstaendige Automation oder als Teil von Blueprint 1 genutzt werden.

```yaml
alias: "KP: Mischtank-Messwerte zurueckmelden"
description: >
  Sendet gemessene EC/pH aus dem Mischtank an Kamerplanter.
  Trigger: Manuell (Button) oder am Ende einer Misch-Automation.
trigger:
  - platform: state
    entity_id: input_boolean.mixing_complete
    to: "on"
condition:
  # EC-Sensor muss validen Wert haben
  - condition: template
    value_template: >
      {{ states('sensor.mixing_tank_ec') | float(0) > 0 }}
action:
  - service: rest_command.kp_mixing_feedback
    data:
      measured_ec: "{{ states('sensor.mixing_tank_ec') | float }}"
      measured_ph: "{{ states('sensor.mixing_tank_ph') | float }}"
      tank_volume: 50.0
  # EC-Abweichungspruefung
  - choose:
      - conditions:
          - condition: template
            value_template: >
              {{ (states('sensor.mixing_tank_ec') | float -
                  states('sensor.kp_run001_current_phase_ec') | float) | abs > 0.3 }}
        sequence:
          - service: notify.mobile_app_phone
            data:
              title: "EC-Abweichung!"
              message: >
                Gemessen: {{ states('sensor.mixing_tank_ec') }} mS,
                Ziel: {{ states('sensor.kp_run001_current_phase_ec') }} mS.
                Abweichung: {{ (states('sensor.mixing_tank_ec') | float - states('sensor.kp_run001_current_phase_ec') | float) | abs | round(2) }} mS.
                Dosierungen pruefen!
  # Reset
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.mixing_complete
mode: single
```

**Voraussetzungen:** E-004-009, E-004-010, API-004-003

---

### Blueprint 5: KP — Multi-Channel Mischung (Fertigation-Channel)

**Beschreibung:** Fuer Multi-Channel-Setups: Steuert nur den Fertigation-Channel (Tank/Tropfer). Andere Channels (Drench, Foliar, Top-Dress) werden manuell oder ueber separate Automationen abgewickelt.

```yaml
alias: "KP: Fertigation-Channel mischen"
description: >
  Mischt den Fertigation-Channel (Tropfer/Tank).
  Nur tank-safe Duenger. Getrennt von Drench/Foliar-Channels.
trigger:
  - platform: template
    value_template: >
      {% set channels = state_attr('sensor.kp_run001_mixing_recipe', 'active_channels_json') %}
      {% if channels %}
        {% for ch in channels | from_json %}
          {% if ch.channel_id == 'dripper-base' and ch.due_today %}
            true
          {% endif %}
        {% endfor %}
      {% endif %}
condition:
  - condition: state
    entity_id: binary_sensor.kp_run001_flushing_active
    state: "off"
action:
  # Fertigation-spezifische Mischsequenz
  # (analog zu Blueprint 1, aber nur mit tank-safe Duengern des Fertigation-Channels)
  - service: notify.mobile_app_phone
    data:
      title: "Fertigation-Channel faellig"
      message: >
        Tropfer-Mischung fuer Run 001 wird vorbereitet.
        Channel: dripper-base
mode: single
```

---

## 7. Optionalitaet & Degradation

| Feature aus REQ-004 | Ohne HA? | Manueller Fallback | HA-Ausfall-Verhalten |
|----------------------|----------|-------------------|---------------------|
| Dosierungs-Berechnung | **Ja** | KP-WebUI zeigt Mischrezept (NutrientPlanDetailPage) | Keine Einschraenkung — Berechnung laeuft vollstaendig auf KP |
| Mischanlage steuern | **Nein** (HA-exklusiv) | Manuelles Mischen nach KP-Anzeige (Step-by-Step-Anleitung) | Pumpen bleiben AUS (sicher). Grower mischt manuell. ESPHome-Watchdog schaltet Pumpen nach 120s automatisch ab |
| EC/pH-Feedback | **Ja** | Manuelles Eintragen im KP-WebUI (`POST /feeding-events`) | Feedback-Luecke. KP arbeitet ohne gemessene Werte weiter, RunoffAnalyzer hat keine aktuellen Daten |
| Giesstermin-Planung | **Ja** | KP generiert Celery-Tasks + zeigt in UI (REQ-006/REQ-022) | Keine Einschraenkung — WateringScheduleEngine ist Backend-seitig |
| Flushing-Protokoll | **Ja** | KP zeigt Flush-Schedule in UI. Grower giesst manuell nur Wasser | Keine Einschraenkung — FlushingProtocol ist Backend-Logik |
| Inventar-Tracking | **Ja** | KP-WebUI zeigt Bestaende und Warnungen | Keine Einschraenkung — FertilizerStock ist Backend-seitig |
| Nachbestell-Warnung (HA-Push) | **Nein** (HA-exklusiv) | KP-WebUI zeigt Stock-Warnung. Kein Push ohne HA/Notification-System | Warnung nur in KP-WebUI sichtbar, kein Push auf Handy |

**Fail-Safe-Zusammenfassung:**

| Ausfall-Szenario | Verhalten | Risiko |
|-----------------|-----------|--------|
| KP-Backend offline | HA nutzt RestoreEntity (letztes bekanntes Rezept). Stale-Markierung nach 2x Polling-Zyklen (600s). Kein automatisches Mischen bis KP wieder da. | Niedrig — kein Mischen ist sicherer als falsches Mischen |
| HA offline | KP generiert weiterhin Tasks (Celery). Grower sieht Mischrezept in WebUI und mischt manuell. | Niedrig — manueller Fallback funktioniert |
| ESPHome/ESP32 offline | HA erkennt `unavailable`. Pumpen bleiben AUS (Fail-Safe durch Watchdog). | Niedrig — ESPHome-Watchdog 120s |
| EC-Sensor defekt | HA liest `unavailable`. Blueprint 1 ueberspringt Phase 5/6 (Messung/pH-Korrektur). Warnung an Grower: "Manuell messen!" | Mittel — pH-Korrektur muss manuell erfolgen |
| pH-Sensor defekt | Wie EC-Sensor. pH-Korrektur wird uebersprungen. | Mittel |

---

## 8. Abhaengigkeiten und Reihenfolge

### Voraussetzungen (muss vorher existieren)

- [x] HA-CUSTOM-INTEGRATION.md HA-001: Config Flow (URL + API-Key + Tenant)
- [x] HA-CUSTOM-INTEGRATION.md HA-002: Device Registry
- [x] HA-CUSTOM-INTEGRATION.md HA-003: Entity Registry (Basis-Entities)
- [x] HA-CUSTOM-INTEGRATION.md HA-004: Coordinator-Pattern
- [x] HA-CUSTOM-INTEGRATION.md HA-NFR-001 bis HA-NFR-007: Architektur-Patterns
- [x] Backend: REQ-004 NutrientPlan-CRUD (implementiert)
- [x] Backend: REQ-004 `current-dosages` Endpoint (implementiert)
- [x] Backend: REQ-004 NutrientSolutionCalculator (implementiert)
- [x] Backend: REQ-004 FlushingProtocol (implementiert)
- [x] Backend: REQ-004 WateringScheduleEngine (implementiert)
- [x] Backend: REQ-013 PlantingRun + RUN_FOLLOWS_PLAN (implementiert)
- [x] Backend: REQ-014 TankManagement (implementiert)
- [ ] Backend: **NEU** API-004-001 `mixing-summary` Endpoint
- [ ] Backend: **NEU** API-004-002 `stock-forecast` Endpoint
- [ ] Backend: **NEU** API-004-003 `mixing-feedback` Endpoint

### Blockiert (kann erst danach)

- [ ] Blueprint 1 (Automatisches Mischen): Braucht API-004-001 + API-004-003 + NutrientCoordinator
- [ ] Blueprint 4 (Feedback): Braucht API-004-003
- [ ] FertilizerStock-Entities: Braucht API-004-002
- [ ] Multi-Channel-Blueprints: Braucht REQ-004 Multi-Channel Delivery Implementierung (derzeit spezifiziert, nicht implementiert)
- [ ] MQTT-Events (EVT-004-001/002): Braucht MQTT-Infrastruktur im Backend (noch nicht implementiert, in HA-CUSTOM-INTEGRATION.md als zukuenftiges Upgrade markiert)

### Implementierungsreihenfolge (empfohlen)

1. **API-004-001** (`mixing-summary`): Zentraler Endpoint, alle HA-Entities haengen davon ab
2. **NutrientCoordinator**: Polling gegen `mixing-summary`
3. **Sensor-Entities** (E-004-001 bis E-004-014): Abgeleitet aus Coordinator-Daten
4. **API-004-003** (`mixing-feedback`): Feedback-Loop
5. **Button-Entity** (E-004-015): Confirm-Aktion
6. **Blueprints**: Automationen die auf den Entities aufbauen
7. **API-004-002** (`stock-forecast`): FertilizerStock-Entities
8. **FertilizerStockCoordinator**: Nachbestell-Logik
9. **MQTT-Events**: Wenn MQTT-Infrastruktur verfuegbar (optional, Polling reicht als MVP)

---

## 9. Offene Fragen

| # | Frage | Kontext | Empfehlung |
|---|-------|---------|------------|
| Q-001 | Soll `mixing-summary` pro PlantingRun oder pro Location aggregieren? | Ein Run hat einen Plan, aber eine Location kann mehrere Runs haben. Die Mischanlage bedient typisch einen Tank, der einer Location zugeordnet ist. | Pro PlantingRun (1:1 Run->Plan). Bei Multi-Run-Locations: Separate Tanks pro Run, oder manuelle Aggregation durch Grower. |
| Q-002 | Wie wird die Pumpen-Kalibrierung (ml/s pro Pumpe) gespeichert? | Blueprint 1 braucht `pump_rate_ml_s` pro Pumpe, um Laufzeiten zu berechnen. Das ist HA-seitige Hardware-Konfiguration, nicht KP-seitig. | `input_number.pump_calmag_ml_per_second` als HA-Helper. Nicht in KP speichern — Pumpen-Kalibrierung ist HA-Hardware. |
| Q-003 | Soll der Feedback-Endpoint automatisch FeedingEvents fuer alle Pflanzen im Run erstellen? | `mixing-feedback` betrifft den Tank. Aber FeedingEvents sind pro PlantInstance. | Ja — Backend erzeugt pro PlantInstance im Run ein FeedingEvent mit den gemessenen Werten. Gleiche Logik wie `watering-events/confirm` (schon implementiert). |
| Q-004 | Multi-Channel: Braucht die Mischanlage pro Channel ein eigenes `mixing-summary`? | Bei Multi-Channel kann der Fertigation-Channel andere Dosierungen haben als der Drench-Channel. | `mixing-summary` liefert `active_channels[]` mit pro-Channel-Dosierungen. Die HA-Automation entscheidet welchen Channel sie bedient (typisch: Fertigation). |
| Q-005 | Wie wird der Tank-Fuellstand fuer die Mischanlage ermittelt? | Blueprint 1 braucht das Tank-Volumen fuer `dosage_N_total_ml = ml_per_liter * volume`. | Option A: Aus REQ-014 TankState (`fill_level_percent * tank_capacity`). Option B: Fester Wert als `input_number.mixing_tank_volume`. Empfehlung: Option B fuer Einfachheit, Option A fuer Praezision. |
| Q-006 | Maximale Anzahl Dosierungen als Entity-Attribute? | HA-Attribute haben keine technische Grenze, aber zu viele Attribute sind schlecht lesbar. | Max 10 Dosierungen (`dosage_1` bis `dosage_10`). REQ-004 NutrientPlanPhaseEntry hat typisch 3-6 Duenger. 10 ist ausreichend. |
| Q-007 | Soll es einen `number.kp_{run}_tank_volume` Entity geben? | Die Mischanlage braucht das Ziel-Volumen. KP kennt die Tank-Kapazitaet (REQ-014), aber nicht den aktuellen Fuellstand des Mischtanks. | Nein — Tank-Volumen ist HA-seitiger Input (`input_number`). KP liefert `ml_per_liter`, HA multipliziert mit dem tatsaechlichen Volumen. |
| Q-008 | Soll `mixing-feedback` den NutrientPlan-Validator triggern (EC-Budget-Abgleich Soll/Ist)? | Wenn die gemessene EC systematisch von der berechneten EC abweicht, koennte KP die Dosierungen korrigieren (geschlossener Regelkreis). | Phase 2 Feature. Fuer MVP: Nur Logging und Warnung. Automatische Dosierungsanpassung ist ein eigenes REQ. |
