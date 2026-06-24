---
title: Local Setup
audience:
  - maintainers
content_mode: how-to
track: developer-docs
last_updated: 2026-06-24
---
# Local Setup

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | 3.12+ |
| **Kubernetes** | Local Kind cluster with Skaffold |
| **Home Assistant** | StatefulSet `homeassistant-0` in namespace `default` |

Kind (Kubernetes IN Docker) runs a local cluster. `homeassistant-0` is the HA StatefulSet pod name.

## Development Workflow

Skaffold does **not** deploy the HA integration automatically. You deploy it by hand via `kubectl cp` and a container restart.

### Deploy Cycle

Run the following steps in order. Each step builds on the previous one:

- lint the source
- copy it into the pod
- clear the cached bytecode
- restart the process
- wait for readiness
- finally inspect the logs

```bash
# 1. Lint check
ruff check custom_components/kamerplanter/
ruff format --check custom_components/kamerplanter/

# 2. Copy files
kubectl cp custom_components/kamerplanter/ \
  default/homeassistant-0:/config/custom_components/kamerplanter/

# 3. Clear bytecode cache (REQUIRED)
kubectl exec homeassistant-0 -n default -- \
  rm -rf /config/custom_components/kamerplanter/__pycache__

# 4. Restart HA process
kubectl exec homeassistant-0 -n default -- kill 1

# 5. Wait for ready
kubectl wait --for=condition=ready pod/homeassistant-0 -n default --timeout=120s

# 6. Check logs
kubectl logs homeassistant-0 -n default --since=90s | \
  grep -iE "(kamerplanter|error|exception)" | tail -30
```

!!! danger "Do NOT use `kubectl delete pod`!"
    The InitContainer `copy-ha-integration` would overwrite manually copied files with the old image. `kill 1` only terminates the HA process — the container restarts without running InitContainers.

### Claude Code Agents

| Agent | Description |
|-------|------------|
| `ha-integration-deploy` | Deploys the integration and checks logs (provided by the `claude-home-assistant` plugin) |
| `ha-integration-verify` | Checks current status without redeployment (provided by the `claude-home-assistant` plugin) |

!!! note "Manual entry points"
    The `Taskfile.yml` targets `deploy-ha` / `verify-ha` remain as manual entry points.

---

## Running Tests

```bash
pip install pytest pytest-asyncio pytest-homeassistant-custom-component aiohttp
pytest tests/ -v --tb=short
```

!!! tip "Faster iteration"
    For individual test files: `pytest tests/test_config_flow.py -v`
