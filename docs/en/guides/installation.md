# Installation

=== "HACS (recommended)"

    1. Open **HACS** in Home Assistant
    2. Click the three dots (top right) and select **Custom repositories**
    3. Add `https://github.com/nolte/kamerplanter-ha` with category **Integration**
    4. Search for **Kamerplanter** and click **Download**
    5. Restart Home Assistant

=== "Manual"

    1. Download the latest release from the [Releases page](https://github.com/nolte/kamerplanter-ha/releases/latest)
    2. Extract and copy `custom_components/kamerplanter/` to your HA `config/custom_components/` directory
    3. Restart Home Assistant

    !!! warning "Directory structure matters"
        The path must be exactly `config/custom_components/kamerplanter/manifest.json` — not nested deeper.

!!! tip "After restart"
    Go to **Settings** > **Integrations** > **Add Integration** and search for "Kamerplanter". The integration only appears after the HA restart.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Home Assistant** | Core **2024.1** or newer |
| **Backend** | Reachable Kamerplanter backend instance |
| **API key** | `kp_` prefix — optional in Light mode |

:material-arrow-right: **Next step:** [Setup](setup.md) — Config flow and token exchange
