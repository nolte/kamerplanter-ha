---
title: Automations
audience:
  - ha-end-users
content_mode: how-to
track: user-docs
last_updated: 2026-06-24
---
# Automations

Kamerplanter entities work right in your HA automations. Here are some proven examples.

!!! note "Prerequisite"
    These examples assume you already know the basics of HA automations. If you're new to them, start with the [HA automation docs](https://www.home-assistant.io/docs/automation/).

---

## Phase Change: Switch Light Schedule

Kamerplanter reports a phase change to "flowering". This automation then switches the light schedule to 12/12:

```yaml
alias: "KP: Flowering Start - 12/12 Light"
trigger:
  - platform: state
    entity_id: sensor.kp_northern_lights_phase
    to: "flowering"
action:
  - service: automation.turn_off
    target:
      entity_id: automation.light_18_6_veg
  - service: automation.turn_on
    target:
      entity_id: automation.light_12_12_bloom
  - service: notify.mobile_app_phone
    data:
      title: "Kamerplanter: Flowering started"
      message: "Northern Lights entering flowering. Light switched to 12/12."
```

---

## Pest monitoring (IPM)

The IPM module (Integrated Pest Management) rates pest pressure per plant. When the alert fires, Home Assistant sends a notification:

```yaml
alias: "KP: Pest alert"
trigger:
  - platform: state
    entity_id: binary_sensor.kp_northern_lights_pest_alert
    to: "on"
action:
  - service: notify.mobile_app_phone
    data:
      title: "Pest pressure detected"
      message: >
        Northern Lights: pest pressure
        {{ states('sensor.kp_northern_lights_pest_pressure') }}.
        Last inspection
        {{ states('sensor.kp_northern_lights_last_inspection_days') }} days ago.
```

!!! tip "Check harvest safety"
    `binary_sensor.kp_{key}_harvest_safe` shows whether the pre-harvest interval has elapsed. `sensor.kp_{key}_karenz_remaining` reports the remaining days.

---

## Refill tank

```yaml
alias: "KP: Refill tank"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_main_tank_volume
    below: 10
action:
  - service: notify.mobile_app_phone
    data:
      title: "Tank almost empty!"
      message: >
        Remaining volume: {{ states('sensor.kp_main_tank_volume') }} L.
        Refill now and record the fill event.
```

!!! tip "Record the fill event"
    Record the refill with the [`kamerplanter.fill_tank`](services.md#kamerplanterfill_tank) service — Kamerplanter then updates EC, pH, and solution age.

---

## Actionable Care Notification

Care reminders with action buttons directly in the notification — Done or Skip:

```yaml
alias: "KP: Care Reminder"
trigger:
  - platform: event
    event_type: kamerplanter_care_due
action:
  - service: notify.mobile_app_phone
    data:
      title: "Care due"
      message: "{{ trigger.event.data.message }}"
      data:
        actions:
          - action: "CONFIRM_CARE_{{ trigger.event.data.notification_key }}"
            title: "Done"
          - action: "SKIP_CARE_{{ trigger.event.data.notification_key }}"
            title: "Skip"
```

!!! info "Actionable notifications"
    The action buttons work with the HA Companion App. To confirm, use the [`kamerplanter.confirm_care`](services.md#kamerplanterconfirm_care) service.

---

## Watering Reminder

Use the `days_until_watering` sensor to get timely reminders:

```yaml
alias: "KP: Water tomorrow"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_northern_lights_days_until_watering
    below: 2
action:
  - service: notify.mobile_app_phone
    data:
      title: "Watering due soon"
      message: >
        {{ state_attr('sensor.kp_northern_lights_days_until_watering', 'friendly_name') }}:
        Next watering on {{ states('sensor.kp_northern_lights_next_watering') }}
```

---

## Accessing Phase Attributes via Jinja2 Templates

The `phase_timeline` and `phase` sensors provide structured attributes that Jinja2 templates can combine.

### Retrieve Current Phase Details

```yaml
# Days in current phase (dynamic)
{{ state_attr('sensor.kp_345249_phase_timeline',
              states('sensor.kp_345249_phase')).days }}

# Start date of current phase
{{ state_attr('sensor.kp_345249_phase_timeline',
              states('sensor.kp_345249_phase')).started }}

# Status of current phase (current/completed)
{{ state_attr('sensor.kp_345249_phase_timeline',
              states('sensor.kp_345249_phase')).status }}
```

### Query a Specific Phase Directly

```yaml
# When did the vegetative phase start?
{{ state_attr('sensor.kp_345249_phase_timeline', 'vegetative').started }}

# How many days did germination last?
{{ state_attr('sensor.kp_345249_phase_timeline', 'germination').days }}
```

### Markdown Card with Phase Info

```yaml
type: markdown
content: >
  **{{ states('sensor.kp_345249_phase') | title }}** for
  {{ state_attr('sensor.kp_345249_phase_timeline',
                 states('sensor.kp_345249_phase')).days }} days
  (started: {{ state_attr('sensor.kp_345249_phase_timeline',
                           states('sensor.kp_345249_phase')).started }})

  Next phase: **{{ states('sensor.kp_345249_next_phase') | default('--') }}**
```

!!! tip "General attribute access pattern"
    The pattern `state_attr('sensor.kp_{id}_phase_timeline', states('sensor.kp_{id}_phase'))` works for all Kamerplanter plants and planting runs. Runs expose extra attributes:

    - `phase_week`
    - `phase_progress_pct`
    - `remaining_days`
