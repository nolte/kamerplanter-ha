# Setup

## Prerequisites: Bidirectional API Access

For a full integration, **both systems need mutual API access**:

```mermaid
flowchart LR
    KP["Kamerplanter"] -- "HA Long-Lived\nAccess Token" --> HA["Home Assistant"]
    HA -- "Kamerplanter\nAPI Key (kp_...)" --> KP
```

| Direction | Token | Purpose | Where to create |
|-----------|-------|---------|----------------|
| **HA → Kamerplanter** | Kamerplanter API key (`kp_` prefix) | HA reads plant data, tank values, tasks | Kamerplanter: **Settings** > **API Keys** |
| **Kamerplanter → HA** | HA Long-Lived Access Token | Kamerplanter reads sensor data, controls actuators | Home Assistant: **Profile** > **Long-Lived Access Tokens** |

!!! warning "Both tokens required"
    Without the **Kamerplanter API key**, the HA integration cannot query data. Without the **HA Access Token**, Kamerplanter cannot read sensor data from Home Assistant or control actuators. For read-only use (HA dashboard only), the Kamerplanter API key alone is sufficient.

### Setting Up Tokens

=== "Kamerplanter API Key (HA → Kamerplanter)"

    1. In Kamerplanter: **Settings** > **API Keys** > **New Key**
    2. Copy the generated key (`kp_...`)
    3. In Home Assistant: Enter during the Kamerplanter integration config flow

=== "HA Access Token (Kamerplanter → HA)"

    1. In Home Assistant: **Profile** (bottom left) > **Long-Lived Access Tokens** > **Create Token**
    2. Copy the token
    3. In Kamerplanter: **Settings** > **Home Assistant** > Enter URL and token

---

## Config Flow

After installation, a 4-step wizard guides you through configuration:

### Step 1: Kamerplanter URL

Enter the URL of your Kamerplanter instance:

| Example | URL |
|---------|-----|
| Local | `http://raspberry:8000` or `http://192.168.1.50:8000` |
| External | `https://kamerplanter.example.com` |

!!! info "Automatic health check"
    The integration automatically checks reachability via `/api/health`.

### Step 2: Authentication

| Mode | Description |
|------|------------|
| **Light mode** | No authentication required |
| **API key** | API key with `kp_` prefix (recommended) |
| **Login** | Username and password as fallback |

### Step 3: Select Tenant

For multi-tenant setups (e.g. community gardens), select the desired tenant from the list. For single users, this step is skipped.

### Step 4: Configure Entities

Choose which plants, locations, and tanks should be created as HA entities. By default, all available entities are created.

---

## Reauth & Reconfigure

The integration supports two correction flows, accessible via **Settings** > **Integrations** > **Kamerplanter**:

=== "Reauthentication"

    When your API key has expired or been revoked, HA shows the integration as faulty. Click **Re-authenticate** and enter a new API key.

    !!! tip "When is reauth triggered?"
        HA automatically detects when the API responds with `401 Unauthorized` and shows the reauth flow.

=== "Reconfigure"

    Change the server URL, e.g. after moving the backend to a new address. Click **Configure** > **Change server URL**.

---

## Polling Intervals

Configurable under **Settings** > **Integrations** > **Kamerplanter** > **Configure**:

| Coordinator | Default | Minimum | Data |
|-------------|---------|---------|------|
| **Plant** | 300s | 120s | Plants, phases, dosages, VPD/EC targets |
| **Location** | 300s | 120s | Locations, tanks, fill levels |
| **Run** | 300s | 120s | Planting runs, run status, plant counts |
| **Alert** | 60s | 30s | Overdue tasks, sensor offline |
| **Task** | 300s | 120s | Pending tasks |

!!! tip "Faster alert polling"
    The Alert coordinator intentionally has a shorter default interval (60s) so time-critical notifications arrive faster.
