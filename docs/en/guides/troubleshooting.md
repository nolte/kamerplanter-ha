---
title: Troubleshooting
audience:
  - self-hosting-admin
  - ha-end-users
content_mode: troubleshooting
track: user-docs
last_updated: 2026-06-24
---
# Troubleshooting

## Common Errors

| Error | Cause | Solution |
|-------|-------|---------|
| "Kamerplanter not reachable" | Backend offline or wrong URL | Check URL, start backend |
| "API key invalid" | Key revoked or incorrect | Generate new API key in Kamerplanter, then [reauthenticate](setup.md#reauthentication-reconfigure) |
| Entity shows "unavailable" | Coordinator update failed | Check logs, increase polling interval |
| Integration won't load | Wrong directory structure | Check path: `custom_components/kamerplanter/manifest.json` |
| Entities missing after update | Stale cache | Call [`kamerplanter.clear_cache`](services.md#kamerplanterclear_cache) service |

---

## Diagnostics

Find diagnostics data under **Settings** > **Integrations** > **Kamerplanter** > **Diagnostics**.

Diagnostics include three parts:

- **Configuration:** the URL and the tenant. HA redacts API keys for you.
- **Coordinator status:** the last update, the error count, and the polling interval. Each coordinator gets its own row.
- **Entity overview:** how many entities exist per platform. Platforms are sensor, binary sensor, calendar, todo, and button.

!!! tip "Bug reports"
    Attach the diagnostics file to a bug report. It holds all you need, but no secrets.

---

## Checking Logs

=== "configuration.yaml"

    ```yaml
    logger:
      logs:
        custom_components.kamerplanter: debug
    ```

=== "HA UI"

    **Settings** > **System** > **Logs** and filter for `kamerplanter`.

!!! info "Disable debug logging"
    Debug logging produces many log entries. After troubleshooting, set the level back to `info` or `warning`.
