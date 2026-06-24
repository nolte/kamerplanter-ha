---
title: Lokales Setup
audience:
  - maintainers
content_mode: how-to
track: developer-docs
last_updated: 2026-06-24
---
# Lokales Setup

## Voraussetzungen

| Anforderung | Details |
|-------------|---------|
| **Python** | 3.12+ |
| **Kubernetes** | Lokaler Kind-Cluster mit Skaffold |
| **Home Assistant** | StatefulSet `homeassistant-0` im Namespace `default` |

Kind (Kubernetes IN Docker) betreibt einen lokalen Cluster. `homeassistant-0` ist der Name des HA-StatefulSet-Pods.

## Development-Workflow

Skaffold deployt die HA-Integration **nicht** automatisch. Du deployst sie von Hand per `kubectl cp` und einem Container-Restart.

### Deploy-Zyklus

Führe die folgenden Schritte der Reihe nach aus. Jeder Schritt baut auf dem vorherigen auf:

- Quellcode linten
- in den Pod kopieren
- den Bytecode-Cache löschen
- den Prozess neu starten
- auf Ready warten
- zuletzt die Logs prüfen

```bash
# 1. Lint prüfen
ruff check custom_components/kamerplanter/
ruff format --check custom_components/kamerplanter/

# 2. Dateien kopieren
kubectl cp custom_components/kamerplanter/ \
  default/homeassistant-0:/config/custom_components/kamerplanter/

# 3. Bytecode-Cache löschen (PFLICHT)
kubectl exec homeassistant-0 -n default -- \
  rm -rf /config/custom_components/kamerplanter/__pycache__

# 4. HA-Prozess neustarten
kubectl exec homeassistant-0 -n default -- kill 1

# 5. Warten auf Ready
kubectl wait --for=condition=ready pod/homeassistant-0 -n default --timeout=120s

# 6. Logs prüfen
kubectl logs homeassistant-0 -n default --since=90s | \
  grep -iE "(kamerplanter|error|exception)" | tail -30
```

!!! danger "NICHT `kubectl delete pod` verwenden!"
    Der InitContainer `copy-ha-integration` würde die manuell kopierten Dateien mit dem alten Image überschreiben. `kill 1` beendet nur den HA-Prozess — der Container startet neu ohne InitContainers.

### Claude Code Agents

| Agent | Beschreibung |
|-------|-------------|
| `ha-integration-deploy` | Deployt die Integration und prüft die Logs (über das `claude-home-assistant`-Plugin) |
| `ha-integration-verify` | Prüft den aktuellen Status ohne Redeployment (über das `claude-home-assistant`-Plugin) |

!!! note "Manuelle Einstiegspunkte"
    Die `Taskfile.yml`-Targets `deploy-ha` / `verify-ha` bleiben als manuelle Einstiegspunkte bestehen.

---

## Tests ausführen

```bash
pip install pytest pytest-asyncio pytest-homeassistant-custom-component aiohttp
pytest tests/ -v --tb=short
```

!!! tip "Schnellere Iteration"
    Für einzelne Test-Dateien: `pytest tests/test_config_flow.py -v`
