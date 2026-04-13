# Automations

## Phase Change: Switch Light Schedule

When Kamerplanter reports a phase change to "flowering", the light schedule is automatically switched to 12h/12h:

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

## VPD Control with Kamerplanter Target

Kamerplanter provides the optimal VPD target per phase. Home Assistant controls the humidifier:

```yaml
alias: "KP: VPD Control"
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
action:
  - choose:
      - conditions:
          - condition: trigger
            id: vpd_too_high
        sequence:
          - service: switch.turn_on
            target:
              entity_id: switch.humidifier_tent_1
      - conditions:
          - condition: trigger
            id: vpd_ok
        sequence:
          - service: switch.turn_off
            target:
              entity_id: switch.humidifier_tent_1
```

## Low Tank: Refill Reminder

```yaml
alias: "KP: Tank refill"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_main_tank_fill_level
    below: 20
action:
  - service: notify.mobile_app_phone
    data:
      title: "Tank almost empty!"
      message: >
        Fill level: {{ states('sensor.kp_main_tank_fill_level') }}%.
        EC: {{ states('sensor.kp_main_tank_ec') }} mS/cm,
        pH: {{ states('sensor.kp_main_tank_ph') }}
```

## Actionable Care Notification

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

---

## Accessing Phase Attributes via Jinja2 Templates

The `phase_timeline` and `phase` sensors provide structured attributes that can be combined in Jinja2 templates.

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
    The pattern `state_attr('sensor.kp_{id}_phase_timeline', states('sensor.kp_{id}_phase'))` works for all Kamerplanter plants and planting runs. For runs, additional attributes like `phase_week`, `phase_progress_pct`, and `remaining_days` are available.
