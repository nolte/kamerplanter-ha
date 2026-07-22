---
title: Lovelace Custom Cards
audience:
  - ha-end-users
content_mode: how-to
track: user-docs
last_updated: 2026-06-27
---
# Lovelace Custom Cards

The integration ships with 5 custom Lovelace cards. It registers them for you during setup. You don't add any resource by hand.

| Card | Description |
|------|------------|
| `kamerplanter-plant-card` | Plant overview with phase timeline and targets |
| `kamerplanter-mix-card` | Nutrient dosage visualization per channel |
| `kamerplanter-tank-card` | Tank status with fill level and solution age |
| `kamerplanter-care-card` | Care reminders with confirm/skip actions |
| `kamerplanter-houseplant-card` | Simplified card for houseplant monitoring |

!!! info "Auto-registration"
    The integration serves the cards from its `www/` directory. You don't add them as Lovelace resources by hand.

## Configuration

Configure all cards via the standard HA editor. You pick the entity in the editor, so no YAML is required.

=== "Plant Card"

    Shows the current phase, days in phase, and phase progression.

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

## Troubleshooting

### Cards don't show in the card picker

The integration registers the cards automatically during setup. If they still don't appear in the picker, your browser loaded the card list **before** registration finished — the cards themselves are fine.

1. Hard-reload the page: `Ctrl + Shift + R` (macOS: `Cmd + Shift + R`).
2. If that doesn't help, clear the browser cache for your HA address.
3. In the **Companion app** (Android/iOS): `Settings → Companion App → Reset frontend cache`, then restart the app.

!!! tip "Immediate workaround"
    You can add any card without the picker: `Add card → Manual` and enter, for example, `type: custom:kamerplanter-plant-card`.

### Check whether the cards are loaded

On the HA page, open the browser console (`F12`) and enter:

```js
window.customCards
```

- If the output contains `kamerplanter-*` entries, it was only the cache — they appear in the picker after the reload.
- If the list is empty or has no `kamerplanter` entries, check the **Network tab** for the `/kamerplanter/...js` files loading with status 200, and the **Console tab** for red errors during load.

### Verify the resources

Under `Settings → Dashboards → ⋮ → Resources` there must be five entries with the URL `/kamerplanter/...js` and type `JavaScript Module`. If they are missing, reload the integration (`Settings → Devices & Services → Kamerplanter → ⋮ → Reload`).

!!! note "YAML mode"
    If your Lovelace runs in YAML mode (`lovelace: mode: yaml` in `configuration.yaml`), the integration cannot register the resources automatically. Add them yourself:

    ```yaml
    lovelace:
      mode: yaml
      resources:
        - url: /kamerplanter/kamerplanter-plant-card.js
          type: module
        - url: /kamerplanter/kamerplanter-mix-card.js
          type: module
        - url: /kamerplanter/kamerplanter-tank-card.js
          type: module
        - url: /kamerplanter/kamerplanter-care-card.js
          type: module
        - url: /kamerplanter/kamerplanter-houseplant-card.js
          type: module
    ```
