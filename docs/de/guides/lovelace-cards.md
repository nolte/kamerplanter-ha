# Lovelace Custom Cards

Die Integration liefert 5 Custom Lovelace Cards mit, die beim Setup automatisch registriert werden:

| Card | Beschreibung |
|------|-------------|
| `kamerplanter-plant-card` | Pflanzen-Uebersicht mit Phasen-Timeline |
| `kamerplanter-mix-card` | Naehrstoff-Dosierung pro Kanal visualisiert |
| `kamerplanter-tank-card` | Tank-Status mit Fuellstand und Loesungsalter |
| `kamerplanter-care-card` | Pflege-Erinnerungen mit Bestaetigen/Ueberspringen |
| `kamerplanter-houseplant-card` | Vereinfachte Card fuer Zimmerpflanzen |

Die Cards werden aus dem `www/`-Verzeichnis der Integration geladen — keine manuelle Ressourcen-Registrierung noetig.

## Konfiguration

Alle Cards koennen ueber den Standard-HA-Editor konfiguriert werden (Entity-Picker, keine YAML-Pflicht).

### Plant Card

```yaml
type: custom:kamerplanter-plant-card
entity: sensor.kp_northern_lights_phase
```

### Mix Card

```yaml
type: custom:kamerplanter-mix-card
entity: sensor.kp_12345_giesswasser_mix
```

### Tank Card

```yaml
type: custom:kamerplanter-tank-card
entity: sensor.kp_90639_info
```

### Care Card

```yaml
type: custom:kamerplanter-care-card
entity: binary_sensor.kp_care_overdue
```

### Houseplant Card

```yaml
type: custom:kamerplanter-houseplant-card
entity: sensor.kp_monstera_phase
```
