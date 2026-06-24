---
title: Installation
audience:
  - ha-end-users
  - self-hosting-admin
content_mode: how-to
track: user-docs
last_updated: 2026-06-24
---
# Installation

Choose your installation method below.

=== "HACS (Home Assistant Community Store) (recommended)"

    1. Open **HACS** in Home Assistant
    2. Click the three dots (top right) and select **Custom repositories**
    3. Add `https://github.com/nolte/kamerplanter-ha` with category **Integration**
    4. Search for **Kamerplanter** and click **Download**
    5. Restart Home Assistant

=== "Manual"

    1. Download the latest release from the [Releases page](https://github.com/nolte/kamerplanter-ha/releases/latest)
    2. Extract the archive. Copy `custom_components/kamerplanter/` to `config/custom_components/`
    3. Restart Home Assistant

    !!! warning "Directory structure matters"
        The path must be exactly `config/custom_components/kamerplanter/manifest.json`. Do not nest it deeper.

!!! tip "After restart"
    Go to **Settings** > **Integrations** > **Add Integration**. Search for "Kamerplanter". It only appears after the HA restart.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Home Assistant** | Core **2024.1** or newer |
| **Backend** | Reachable Kamerplanter backend instance |
| **API key** | `kp_` prefix — optional in Light mode |

:material-arrow-right: **Next step:** [Setup](setup.md) — Config flow and token exchange
