# Lovelace Custom Cards

The integration ships with 5 custom Lovelace cards that are auto-registered on setup:

| Card | Description |
|------|------------|
| `kamerplanter-plant-card` | Plant instance overview with phase timeline |
| `kamerplanter-mix-card` | Nutrient dosage visualization per channel |
| `kamerplanter-tank-card` | Tank status with fill level and solution age |
| `kamerplanter-care-card` | Care reminders with confirm/skip actions |
| `kamerplanter-houseplant-card` | Simplified card for houseplant monitoring |

Cards are served from the integration's `www/` directory — no manual resource registration needed.

## Configuration

All cards can be configured via the standard HA editor (entity picker, no YAML required).

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
