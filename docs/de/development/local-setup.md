# Lokales Setup

## Voraussetzungen

| Anforderung | Details |
|-------------|---------|
| **Python** | 3.12+ |
| **Kubernetes** | Lokaler Kind-Cluster mit Skaffold |
| **Home Assistant** | StatefulSet `homeassistant-0` im Namespace `default` |

## Development-Workflow

Die HA-Integration wird **nicht** automatisch per Skaffold deployed, sondern manuell per `kubectl cp` und Container-Restart.

### Deploy-Zyklus

```bash
# 1. Lint pruefen
ruff check custom_components/kamerplanter/
ruff format --check custom_components/kamerplanter/

# 2. Dateien kopieren
kubectl cp custom_components/kamerplanter/ \
  default/homeassistant-0:/config/custom_components/kamerplanter/

# 3. Bytecode-Cache loeschen (PFLICHT)
kubectl exec homeassistant-0 -n default -- \
  rm -rf /config/custom_components/kamerplanter/__pycache__

# 4. HA-Prozess neustarten
kubectl exec homeassistant-0 -n default -- kill 1

# 5. Warten auf Ready
kubectl wait --for=condition=ready pod/homeassistant-0 -n default --timeout=120s

# 6. Logs pruefen
kubectl logs homeassistant-0 -n default --since=90s | \
  grep -iE "(kamerplanter|error|exception)" | tail -30
```

!!! danger "NICHT `kubectl delete pod` verwenden!"
    Der InitContainer `copy-ha-integration` wuerde die manuell kopierten Dateien mit dem alten Image ueberschreiben. `kill 1` beendet nur den HA-Prozess — der Container restartet ohne InitContainers.

### Claude Code Skills

| Skill | Beschreibung |
|-------|-------------|
| `/deploy-ha` | Deployt die Integration und prueft die Logs |
| `/verify-ha` | Prueft den aktuellen Status ohne Redeployment |

---

## Tests ausfuehren

```bash
pip install pytest pytest-asyncio pytest-homeassistant-custom-component aiohttp
pytest tests/ -v --tb=short
```

!!! tip "Schnellere Iteration"
    Fuer einzelne Test-Dateien: `pytest tests/test_config_flow.py -v`
