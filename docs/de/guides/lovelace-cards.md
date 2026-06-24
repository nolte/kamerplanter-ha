---
title: Lovelace Custom Cards
audience:
  - ha-end-users
content_mode: how-to
track: user-docs
last_updated: 2026-06-24
---
# Lovelace Custom Cards

Die Integration liefert 5 Custom Lovelace Cards mit. Sie registriert die Cards beim Setup für dich. Du legst keine Ressource von Hand an.

| Card | Beschreibung |
|------|-------------|
| `kamerplanter-plant-card` | Pflanzen-Übersicht mit Phasen-Timeline und Sollwerten |
| `kamerplanter-mix-card` | Nährstoff-Dosierung pro Kanal visualisiert |
| `kamerplanter-tank-card` | Tank-Status mit Füllstand und Lösungsalter |
| `kamerplanter-care-card` | Pflege-Erinnerungen mit Bestätigen/Überspringen |
| `kamerplanter-houseplant-card` | Vereinfachte Card für Zimmerpflanzen |

!!! info "Auto-Registrierung"
    Die Integration lädt die Cards aus ihrem `www/`-Verzeichnis. Du fügst sie nicht von Hand als Lovelace-Ressource hinzu.

## Konfiguration

Konfiguriere alle Cards über den Standard-HA-Editor. Du wählst die Entity im Editor aus, YAML ist also nicht nötig.

=== "Plant Card"

    Zeigt die aktuelle Phase, Tage in Phase und den Phasenverlauf.

    ```yaml
    type: custom:kamerplanter-plant-card
    entity: sensor.kp_northern_lights_phase
    ```

=== "Mix Card"

    Visualisiert die Dünger-Dosierung pro Kanal mit Mengenangaben in ml/L.

    ```yaml
    type: custom:kamerplanter-mix-card
    entity: sensor.kp_12345_giesswasser_mix
    ```

=== "Tank Card"

    Zeigt Füllstand, Volumen und Lösungsalter des Tanks.

    ```yaml
    type: custom:kamerplanter-tank-card
    entity: sensor.kp_90639_info
    ```

=== "Care Card"

    Listet fällige Pflege-Aufgaben mit Bestätigen/Überspringen-Buttons.

    ```yaml
    type: custom:kamerplanter-care-card
    entity: binary_sensor.kp_care_overdue
    ```

=== "Houseplant Card"

    Vereinfachte Darstellung für Zimmerpflanzen ohne komplexe Nährstoffdaten.

    ```yaml
    type: custom:kamerplanter-houseplant-card
    entity: sensor.kp_monstera_phase
    ```
