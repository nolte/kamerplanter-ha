# Entities

The integration automatically creates entities for all selected plants, locations, and tanks. Each entity belongs to one of the [5 coordinators](../development/architecture.md#coordinators-coordinatorpy) and updates at its polling interval.

---

## Plant Sensors

**Per plant instance** (Plant Coordinator):

| Entity | Description | Example |
|--------|------------|---------|
| `sensor.kp_{key}_phase` | Current growth phase | `flowering` |
| `sensor.kp_{key}_days_in_phase` | Days in current phase | `14` |
| `sensor.kp_{key}_nutrient_plan` | Assigned nutrient plan | `Bloom Week 3` |
| `sensor.kp_{key}_phase_timeline` | Phase progression with attributes | see [Templates](automations.md#accessing-phase-attributes-via-jinja2-templates) |
| `sensor.kp_{key}_next_phase` | Next planned phase | `ripening` |
| `sensor.kp_{key}_vpd_target` | VPD target for current phase (kPa) | `1.2` |
| `sensor.kp_{key}_ec_target` | EC target for current phase (mS/cm) | `1.8` |
| `sensor.kp_{key}_days_until_watering` | Days until next watering | `2` |
| `sensor.kp_{key}_next_watering` | Next watering date | `2026-04-16` |
| `sensor.kp_{key}_active_channels` | Active nutrient channels | `2` |
| `sensor.kp_{key}_{channel}_mix` | Mixing ratio per channel (ml/L) | Attributes: fertilizer amounts |

!!! info "Phase enum values"
    Possible values for `_phase`: `germination`, `seedling`, `vegetative`, `flowering`, `ripening`, `harvest`, `dormancy`, `flushing`, `drying`, `curing`, `juvenile`, `climbing`, `mature`, `senescence`, `leaf_phase`, `short_day_induction`

---

## Run Sensors

**Per planting run** (Run Coordinator):

| Entity | Description | Example |
|--------|------------|---------|
| `sensor.kp_{key}_status` | Run status | `active` |
| `sensor.kp_{key}_plant_count` | Number of plants in run | `6` |
| `sensor.kp_{key}_nutrient_plan` | Run's nutrient plan | `Grow Master` |
| `sensor.kp_{key}_phase_timeline` | Run phase progression | Attributes per phase |
| `sensor.kp_{key}_next_phase` | Next phase | `flowering` |
| `sensor.kp_{key}_{channel}_mix` | Mixing ratio per channel | Attributes: fertilizer amounts |

!!! tip "Run-specific attributes"
    Runs provide additional attributes on the `phase_timeline` sensor: `phase_week`, `phase_progress_pct`, and `remaining_days`.

---

## Location Sensors

**Per location** (Location Coordinator):

| Entity | Description | Example |
|--------|------------|---------|
| `sensor.kp_loc_{key}_type` | Location type | `tent` |
| `sensor.kp_loc_{key}_active_run_count` | Number of active runs | `1` |
| `sensor.kp_loc_{key}_active_plant_count` | Number of active plants | `4` |
| `sensor.kp_loc_{key}_plant_count` | Total plant count | `6` |
| `sensor.kp_loc_{key}_run_status` | Active run status | `active` |
| `sensor.kp_loc_{key}_run_phase` | Active run phase | `vegetative` |
| `sensor.kp_loc_{key}_run_days_in_phase` | Days in current phase | `21` |
| `sensor.kp_loc_{key}_run_nutrient_plan` | Run's nutrient plan | `Veg Standard` |
| `sensor.kp_loc_{key}_run_next_phase` | Next phase | `flowering` |
| `sensor.kp_loc_{key}_{channel}_mix` | Mixing ratio per channel | Attributes: fertilizer amounts |

---

## Tank Sensors

**Per tank** (Location Coordinator):

| Entity | Description | Example |
|--------|------------|---------|
| `sensor.kp_{key}_info` | Tank info (name, type) | `Main Tank` |
| `sensor.kp_{key}_volume` | Current volume (L) | `45.0` |
| `sensor.kp_{key}_fill_level` | Fill level in percent | `75` |

---

## Server Sensors

| Entity | Description | Example |
|--------|------------|---------|
| `sensor.kp_tasks_due_today` | Tasks due today | `3` |
| `sensor.kp_tasks_overdue` | Overdue tasks | `1` |
| `sensor.kp_next_watering` | Next watering date | `2026-04-15` |

---

## Binary Sensors

| Entity | Description | Coordinator |
|--------|------------|-------------|
| `binary_sensor.kp_{key}_needs_attention` | Plant has overdue tasks | Alert |
| `binary_sensor.kp_loc_{key}_needs_attention` | Location has overdue tasks | Alert |
| `binary_sensor.kp_sensor_offline` | At least one sensor is offline | Alert |
| `binary_sensor.kp_care_overdue` | Care tasks overdue | Alert |

!!! example "Use in automations"
    ```yaml
    trigger:
      - platform: state
        entity_id: binary_sensor.kp_care_overdue
        to: "on"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Care overdue!"
          message: "At least one care task is overdue."
    ```

---

## Calendar, Todo, Button

| Entity | Description | Coordinator |
|--------|------------|-------------|
| `calendar.kp_phases` | Growth phases as multi-day events | Plant |
| `calendar.kp_tasks` | Pending tasks with due dates | Task |
| `todo.kp_tasks` | Task list — checking off marks tasks as done in the backend | Task |
| `button.kp_refresh_all` | Manual refresh of all coordinators | — |

!!! tip "Todo sync"
    When you check off a task in the HA todo list, it's automatically marked as done in the Kamerplanter backend. This also fires a `kamerplanter_task_completed` event.

---

## Events

The integration fires events that you can use as triggers in automations:

| Event | Description |
|-------|------------|
| `kamerplanter_phase` | Phase transition for a plant or run |
| `kamerplanter_care_due` | Care reminder due |
| `kamerplanter_task_due` | Task due |
| `kamerplanter_task_completed` | Task checked off via todo entity |
| `kamerplanter_tank_alert` | Tank alert (low level, old solution) |
| `kamerplanter_harvest` | Harvest notification |
| `kamerplanter_ipm_alert` | Pest/disease alert |
| `kamerplanter_sensor_alert` | Sensor offline or threshold exceeded |
| `kamerplanter_weather_alert` | Weather warning |
| `kamerplanter_seasonal` | Seasonal reminder |
| `kamerplanter_data_refreshed` | Manual refresh via button |

!!! example "Event as trigger"
    ```yaml
    trigger:
      - platform: event
        event_type: kamerplanter_phase
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.new_phase == 'flowering' }}"
    ```
