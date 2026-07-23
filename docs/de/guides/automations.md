---
title: Automationen
audience:
  - ha-end-users
content_mode: how-to
track: user-docs
last_updated: 2026-07-23
---
# Automationen

Kamerplanter-Entities lassen sich direkt in HA-Automationen nutzen. Hier einige bewährte Beispiele.

!!! note "Voraussetzung"
    Diese Beispiele setzen voraus, dass du die Grundlagen von HA-Automationen kennst. Falls nicht, beginne mit der [HA-Automations-Dokumentation](https://www.home-assistant.io/docs/automation/).

---

## Phasenwechsel: Lichtprogramm umstellen

Kamerplanter meldet einen Phasenwechsel zu "Blüte". Diese Automation stellt das Lichtprogramm dann auf 12/12 um:

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

## Schädlingsüberwachung (IPM)

Das IPM-Modul (Integrierter Pflanzenschutz) bewertet den Schädlingsdruck pro Pflanze. Schlägt der Alarm an, schickt Home Assistant eine Benachrichtigung:

```yaml
alias: "KP: Schädlingsalarm"
trigger:
  - platform: state
    entity_id: binary_sensor.kp_northern_lights_pest_alert
    to: "on"
action:
  - service: notify.mobile_app_phone
    data:
      title: "Schädlingsdruck erkannt"
      message: >
        Northern Lights: Schädlingsdruck
        {{ states('sensor.kp_northern_lights_pest_pressure') }}.
        Letzte Kontrolle vor
        {{ states('sensor.kp_northern_lights_last_inspection_days') }} Tagen.
```

!!! tip "Erntesicherheit prüfen"
    `binary_sensor.kp_{key}_harvest_safe` zeigt an, ob die Karenzzeit (Wartezeit vor der Ernte) abgelaufen ist. `sensor.kp_{key}_karenz_remaining` nennt die verbleibenden Tage.

---

## Tank nachfüllen

```yaml
alias: "KP: Tank nachfüllen"
trigger:
  - platform: numeric_state
    entity_id: sensor.kp_haupttank_volume
    below: 10
action:
  - service: notify.mobile_app_phone
    data:
      title: "Tank fast leer!"
      message: >
        Restvolumen: {{ states('sensor.kp_haupttank_volume') }} L.
        Jetzt nachfüllen und das Füll-Event erfassen.
```

!!! tip "Füll-Event erfassen"
    Erfasse das Nachfüllen mit dem Service [`kamerplanter.fill_tank`](services.md#kamerplanterfill_tank) — Kamerplanter aktualisiert dann EC, pH und Lösungsalter.

---

## Actionable Care Notification

Pflege-Erinnerungen mit Aktions-Buttons direkt in der Benachrichtigung — erledigt oder überspringen:

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

Die Sensoren `phase_timeline` und `phase` stellen strukturierte Attribute bereit. Jinja2-Templates können diese Attribute kombinieren.

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
    Das Muster `state_attr('sensor.kp_{id}_phase_timeline', states('sensor.kp_{id}_phase'))` funktioniert für alle Kamerplanter-Pflanzen und Planting Runs. Bei Runs gibt es zusätzliche Attribute:

    - `phase_week`
    - `phase_progress_pct`
    - `remaining_days`
