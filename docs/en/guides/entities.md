# Entities

The integration automatically creates entities for all selected plants, locations, and tanks.

## Plant Sensors

**Per plant instance:**

| Entity | Description |
|--------|------------|
| `sensor.kp_{key}_phase` | Current growth phase |
| `sensor.kp_{key}_days_in_phase` | Days in current phase |
| `sensor.kp_{key}_nutrient_plan` | Assigned nutrient plan |
| `sensor.kp_{key}_phase_timeline` | Phase progression with attributes |
| `sensor.kp_{key}_next_phase` | Next planned phase |
| `sensor.kp_{key}_active_channels` | Active nutrient channels |
| `sensor.kp_{key}_{channel}_mix` | Mixing ratio per channel (ml/L) |

**Per planting run:**

| Entity | Description |
|--------|------------|
| `sensor.kp_{key}_status` | Run status |
| `sensor.kp_{key}_plant_count` | Number of plants in run |
| `sensor.kp_{key}_nutrient_plan` | Run's nutrient plan |
| `sensor.kp_{key}_phase_timeline` | Run phase progression |
| `sensor.kp_{key}_next_phase` | Next phase |
| `sensor.kp_{key}_{channel}_mix` | Mixing ratio per channel |

## Location Sensors

**Per location:**

| Entity | Description |
|--------|------------|
| `sensor.kp_loc_{key}_type` | Location type |
| `sensor.kp_loc_{key}_active_run_count` | Number of active runs |
| `sensor.kp_loc_{key}_active_plant_count` | Number of active plants |
| `sensor.kp_loc_{key}_run_phase` | Active run phase |
| `sensor.kp_loc_{key}_run_days_in_phase` | Days in current phase |
| `sensor.kp_loc_{key}_run_nutrient_plan` | Run's nutrient plan |
| `sensor.kp_loc_{key}_run_next_phase` | Next phase |
| `sensor.kp_loc_{key}_{channel}_mix` | Mixing ratio per channel |

## Tank Sensors

**Per tank:**

| Entity | Description |
|--------|------------|
| `sensor.kp_{key}_info` | Tank info (name, type) |
| `sensor.kp_{key}_volume` | Current volume |

## Server Sensors

| Entity | Description |
|--------|------------|
| `sensor.kp_tasks_due_today` | Tasks due today |
| `sensor.kp_tasks_overdue` | Overdue tasks |
| `sensor.kp_next_watering` | Next watering date |

## Binary Sensors

| Entity | Description |
|--------|------------|
| `binary_sensor.kp_{key}_needs_attention` | Plant has overdue tasks |
| `binary_sensor.kp_loc_{key}_needs_attention` | Location has overdue tasks |
| `binary_sensor.kp_sensor_offline` | At least one sensor is offline |
| `binary_sensor.kp_care_overdue` | Care tasks overdue |

## Calendar, Todo, Button

| Entity | Description |
|--------|------------|
| `calendar.kp_phases` | Growth phases as multi-day events |
| `calendar.kp_tasks` | Pending tasks with due dates |
| `todo.kp_tasks` | Task list — checking off marks tasks as done in the backend |
| `button.kp_refresh_all` | Manual refresh of all coordinators |

## Events

| Event | Description |
|-------|------------|
| `kamerplanter_task_completed` | Task checked off via todo entity |
| `kamerplanter_data_refreshed` | Manual refresh via button |
| `kamerplanter_care_due` | Care reminder due |
| `kamerplanter_phase` | Phase transition |
| `kamerplanter_tank_alert` | Tank alert (low level, old solution) |
| `kamerplanter_harvest` | Harvest notification |
| `kamerplanter_ipm_alert` | Pest/disease alert |
| `kamerplanter_sensor_alert` | Sensor offline/threshold |
| `kamerplanter_task_due` | Task due |
| `kamerplanter_weather_alert` | Weather warning |
| `kamerplanter_seasonal` | Seasonal reminder |
