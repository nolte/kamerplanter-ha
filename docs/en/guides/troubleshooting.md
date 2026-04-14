# Troubleshooting

## Common Errors

| Error | Cause | Solution |
|-------|-------|---------|
| "Kamerplanter not reachable" | Backend offline or wrong URL | Check URL, start backend |
| "API key invalid" | Key revoked or incorrect | Generate new API key in Kamerplanter, then [reauth](setup.md#reauth--reconfigure) |
| Entity shows "unavailable" | Coordinator update failed | Check logs, increase polling interval |
| Integration won't load | Wrong directory structure | Check path: `custom_components/kamerplanter/manifest.json` |
| Entities missing after update | Stale cache | Call [`kamerplanter.clear_cache`](services.md#kamerplanterclear_cache) service |

---

## Diagnostics

Diagnostics data is available under **Settings** > **Integrations** > **Kamerplanter** > **Diagnostics**.

Diagnostics include:

- **Configuration** — URL, tenant (API keys are automatically redacted)
- **Coordinator status** — last update, error count, polling interval per coordinator
- **Entity overview** — count per platform (sensor, binary sensor, calendar, todo, button)

!!! tip "Bug reports"
    Attach the diagnostics file to bug reports — it contains all relevant info without sensitive data.

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
    Debug logging produces many log entries. Don't forget to set it back to `info` or `warning` after troubleshooting.
