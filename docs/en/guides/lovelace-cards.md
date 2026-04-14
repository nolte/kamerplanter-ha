# Lovelace Custom Cards

The integration ships with 5 custom Lovelace cards that are auto-registered on setup — no manual resource registration needed.

| Card | Description |
|------|------------|
| `kamerplanter-plant-card` | Plant overview with phase timeline and targets |
| `kamerplanter-mix-card` | Nutrient dosage visualization per channel |
| `kamerplanter-tank-card` | Tank status with fill level and solution age |
| `kamerplanter-care-card` | Care reminders with confirm/skip actions |
| `kamerplanter-houseplant-card` | Simplified card for houseplant monitoring |

!!! info "Auto-registration"
    Cards are served from the integration's `www/` directory. You don't need to manually add them as Lovelace resources.

## Configuration

All cards can be configured via the standard HA editor (entity picker, no YAML required).

=== "Plant Card"

    Shows the current phase, days in phase, VPD/EC targets, and phase progression.

    ```yaml
    type: custom:kamerplanter-plant-card
    entity: sensor.kp_northern_lights_phase
    ```

=== "Mix Card"

    Visualizes fertilizer dosages per channel with amounts in ml/L.

    ```yaml
    type: custom:kamerplanter-mix-card
    entity: sensor.kp_12345_giesswasser_mix
    ```

=== "Tank Card"

    Shows fill level, volume, and solution age of the tank.

    ```yaml
    type: custom:kamerplanter-tank-card
    entity: sensor.kp_90639_info
    ```

=== "Care Card"

    Lists due care tasks with confirm/skip buttons.

    ```yaml
    type: custom:kamerplanter-care-card
    entity: binary_sensor.kp_care_overdue
    ```

=== "Houseplant Card"

    Simplified view for houseplants without complex nutrient data.

    ```yaml
    type: custom:kamerplanter-houseplant-card
    entity: sensor.kp_monstera_phase
    ```
