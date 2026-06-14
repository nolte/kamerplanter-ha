# Lovelace Custom Cards

Die Integration liefert 5 Custom Lovelace Cards mit. Sie werden beim Setup automatisch registriert. Eine manuelle Ressourcen-Registrierung ist nicht nötig.

| Card | Beschreibung |
|------|-------------|
| `kamerplanter-plant-card` | Pflanzen-Übersicht mit Phasen-Timeline und Sollwerten |
| `kamerplanter-mix-card` | Nährstoff-Dosierung pro Kanal visualisiert |
| `kamerplanter-tank-card` | Tank-Status mit Füllstand und Lösungsalter |
| `kamerplanter-care-card` | Pflege-Erinnerungen mit Bestätigen/Überspringen |
| `kamerplanter-houseplant-card` | Vereinfachte Card für Zimmerpflanzen |

!!! info "Auto-Registrierung"
    Die Cards werden aus dem `www/`-Verzeichnis der Integration geladen. Du musst sie nicht manuell als Lovelace-Ressource hinzufügen.

## Konfiguration

Alle Cards können über den Standard-HA-Editor konfiguriert werden (Entity-Picker, keine YAML-Pflicht).

=== "Plant Card"

    Zeigt die aktuelle Phase, Tage in Phase, VPD/EC-Sollwerte und den Phasenverlauf.

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
