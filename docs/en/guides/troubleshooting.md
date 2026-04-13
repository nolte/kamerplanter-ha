# Troubleshooting

## Common Errors

| Error | Cause | Solution |
|-------|-------|---------|
| "Kamerplanter not reachable" | Backend offline or wrong URL | Check URL, start backend |
| "API key invalid" | Key revoked or incorrect | Generate new API key in Kamerplanter |
| Entity shows "unavailable" | Coordinator update failed | Check logs, increase polling interval |

## Diagnostics

Diagnostics data is available under **Settings** > **Integrations** > **Kamerplanter** > **Diagnostics**.

Diagnostics include:

- Configuration data (URL, tenant — API keys are automatically redacted)
- Coordinator status (last update, error count)
- Entity overview (count per platform)

## Checking Logs

Filter HA logs for the integration:

```yaml
# In configuration.yaml
logger:
  logs:
    custom_components.kamerplanter: debug
```

Or in the HA UI: **Settings** > **System** > **Logs** and filter for "kamerplanter".
