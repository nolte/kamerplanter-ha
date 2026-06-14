# Automationen

Kamerplanter-Entities lassen sich direkt in HA-Automationen verwenden. Hier einige praxiserprobte Beispiele.

!!! note "Voraussetzung"
    Grundkenntnisse zu HA-Automationen werden vorausgesetzt. Eine Einführung bietet die [HA-Automations-Dokumentation](https://www.home-assistant.io/docs/automation/).

---

## Phasenwechsel: Lichtprogramm umstellen

Kamerplanter meldet einen Phasenwechsel zu "Blüte". Das Lichtprogramm wird dann automatisch auf 12/12 umgestellt:

```yaml
alias: "KP: Bluete-Start - 12/12 Licht"
trigger:
  - platform: state
    entity_id: sensor.kp_northern_lights_phase
    to: "flowering"
action:
  - service: automation.turn_off
    target:
      entity_id: automation.licht_18_6_veg
  - service: automation.turn_on
    target:
      entity_id: automation.licht_12_12_bloom
  - service: notify.mobile_app_phone
    data:
      title: "Kamerplanter: Bluete gestartet"
      message: "Northern Lights wechselt in Bluete. Licht auf 12/12 umgestellt."
```

---

## VPD-Regelung mit Kamerplanter-Sollwert

Kamerplanter liefert den optimalen VPD-Sollwert pro Phase über `sensor.kp_{key}_vpd_target`. Home Assistant regelt den Befeuchter:

```yaml
alias: "KP: VPD-Regelung"
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
              entity_id: switch.befeuchter_zelt_1
      - conditions:
          - condition: trigger
            id: vpd_ok
        sequence:
          - service: switch.turn_off
            target:
              entity_id: switch.befeuchter_zelt_1
```

!!! tip "VPD- und EC-Sollwerte"
    Neben `vpd_target` liefert Kamerplanter auch `ec_target` pro Pflanze. Damit kannst du z.B. die Düngerpumpe regeln oder Warnungen bei Abweichungen auslösen.

---

## Tank nachfüllen

```yaml
alias: "KP: Tank nachfüllen"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_haupttank_fill_level
    below: 20
action:
  - service: notify.mobile_app_phone
    data:
      title: "Tank fast leer!"
      message: >
        Füllstand: {{ states('sensor.kp_haupttank_fill_level') }}%.
        EC: {{ states('sensor.kp_haupttank_ec') }} mS/cm,
        pH: {{ states('sensor.kp_haupttank_ph') }}
```

---

## Actionable Care Notification

Pflege-Erinnerungen mit Aktions-Buttons direkt in der Benachrichtigung — Erledigt oder Überspringen:

```yaml
alias: "KP: Pflege-Erinnerung"
trigger:
  - platform: event
    event_type: kamerplanter_care_due
action:
  - service: notify.mobile_app_phone
    data:
      title: "Pflege fällig"
      message: "{{ trigger.event.data.message }}"
      data:
        actions:
          - action: "CONFIRM_CARE_{{ trigger.event.data.notification_key }}"
            title: "Erledigt"
          - action: "SKIP_CARE_{{ trigger.event.data.notification_key }}"
            title: "Überspringen"
```

!!! info "Actionable Notifications"
    Die Aktions-Buttons funktionieren mit der HA Companion App. Zum Bestätigen verwendest du den Service [`kamerplanter.confirm_care`](services.md#kamerplanterconfirm_care).

---

## Bewässerungs-Erinnerung

Nutze den `days_until_watering`-Sensor, um rechtzeitig zu erinnern:

```yaml
alias: "KP: Morgen gießen"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_northern_lights_days_until_watering
    below: 2
action:
  - service: notify.mobile_app_phone
    data:
      title: "Gießen bald fällig"
      message: >
        {{ state_attr('sensor.kp_northern_lights_days_until_watering', 'friendly_name') }}:
        Naechste Bewasserung am {{ states('sensor.kp_northern_lights_next_watering') }}
```

---

## Phasen-Attribute per Jinja2-Template

Die Sensoren `phase_timeline` und `phase` stellen strukturierte Attribute bereit, die sich in Jinja2-Templates kombinieren lassen.

### Aktuelle Phasen-Details abrufen

```yaml
# Tage in aktueller Phase (dynamisch)
{{ state_attr('sensor.kp_345249_phase_timeline',
              states('sensor.kp_345249_phase')).days }}

# Startdatum der aktuellen Phase
{{ state_attr('sensor.kp_345249_phase_timeline',
              states('sensor.kp_345249_phase')).started }}

# Status der aktuellen Phase (current/completed)
{{ state_attr('sensor.kp_345249_phase_timeline',
              states('sensor.kp_345249_phase')).status }}
```

### Bestimmte Phase direkt abfragen

```yaml
# Wann hat die vegetative Phase begonnen?
{{ state_attr('sensor.kp_345249_phase_timeline', 'vegetative').started }}

# Wie viele Tage hat die Keimung gedauert?
{{ state_attr('sensor.kp_345249_phase_timeline', 'germination').days }}
```

### Markdown-Card mit Phasen-Info

```yaml
type: markdown
content: >
  **{{ states('sensor.kp_345249_phase') | title }}** seit
  {{ state_attr('sensor.kp_345249_phase_timeline',
                 states('sensor.kp_345249_phase')).days }} Tagen
  (Start: {{ state_attr('sensor.kp_345249_phase_timeline',
                         states('sensor.kp_345249_phase')).started }})

  Naechste Phase: **{{ states('sensor.kp_345249_next_phase') | default('--') }}**
```

!!! tip "Attribut-Zugriff allgemein"
    Das Muster `state_attr('sensor.kp_{id}_phase_timeline', states('sensor.kp_{id}_phase'))` funktioniert für alle Kamerplanter-Pflanzen und Planting Runs. Bei Runs stehen zusätzlich `phase_week`, `phase_progress_pct` und `remaining_days` als Attribute zur Verfügung.
