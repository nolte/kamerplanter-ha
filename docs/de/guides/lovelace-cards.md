# Lovelace Custom Cards

Die Integration liefert 5 Custom Lovelace Cards mit, die beim Setup automatisch registriert werden — keine manuelle Ressourcen-Registrierung noetig.

| Card | Beschreibung |
|------|-------------|
| `kamerplanter-plant-card` | Pflanzen-Uebersicht mit Phasen-Timeline und Sollwerten |
| `kamerplanter-mix-card` | Naehrstoff-Dosierung pro Kanal visualisiert |
| `kamerplanter-tank-card` | Tank-Status mit Fuellstand und Loesungsalter |
| `kamerplanter-care-card` | Pflege-Erinnerungen mit Bestaetigen/Ueberspringen |
| `kamerplanter-houseplant-card` | Vereinfachte Card fuer Zimmerpflanzen |

!!! info "Auto-Registrierung"
    Die Cards werden aus dem `www/`-Verzeichnis der Integration geladen. Du musst sie nicht manuell als Lovelace-Ressource hinzufuegen.

## Konfiguration

Alle Cards koennen ueber den Standard-HA-Editor konfiguriert werden (Entity-Picker, keine YAML-Pflicht).

=== "Plant Card"

    Zeigt die aktuelle Phase, Tage in Phase, VPD/EC-Sollwerte und den Phasenverlauf.

    ```yaml
    type: custom:kamerplanter-plant-card
    entity: sensor.kp_northern_lights_phase
    ```

=== "Mix Card"

    Visualisiert die Duenger-Dosierung pro Kanal mit Mengenangaben in ml/L.

    ```yaml
    type: custom:kamerplanter-mix-card
    entity: sensor.kp_12345_giesswasser_mix
    ```

=== "Tank Card"

    Zeigt Fuellstand, Volumen und Loesungsalter des Tanks.

    ```yaml
    type: custom:kamerplanter-tank-card
    entity: sensor.kp_90639_info
    ```

=== "Care Card"

    Listet faellige Pflege-Aufgaben mit Bestaetigen/Ueberspringen-Buttons.

    ```yaml
    type: custom:kamerplanter-care-card
    entity: binary_sensor.kp_care_overdue
    ```

=== "Houseplant Card"

    Vereinfachte Darstellung fuer Zimmerpflanzen ohne komplexe Naehrstoffdaten.

    ```yaml
    type: custom:kamerplanter-houseplant-card
    entity: sensor.kp_monstera_phase
    ```
