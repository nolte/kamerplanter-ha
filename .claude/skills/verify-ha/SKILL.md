---
name: verify-ha
description: "Prueft die laufende HA-Integration auf Fehler: HA-Logs, Entity-Status, Coordinator-Updates. Nutze diesen Skill um den aktuellen Zustand der HA-Integration zu diagnostizieren ohne neu zu deployen."
disable-model-invocation: true
---

# HA-Integration verifizieren

> **Umgebung:** Lokaler Kind-Cluster (Kubernetes in Docker), Skaffold-managed.
> HA laeuft als StatefulSet `homeassistant-0` im Namespace `default`.

## Ausfuehrung

Fuehre den Taskfile-Task aus:

```bash
task verify-ha 2>&1; echo "EXIT:$?"
```

## Ergebnis zusammenfassen

- **Pod-Status:** Running/NotRunning + Uptime
- **Integration geladen:** Ja/Nein (aus Logs)
- **Fehler:** Anzahl + Kategorisierung
- **Letzte Coordinator-Updates:** Timestamps falls sichtbar

Bei Fehlern: Analysiere die Ursache und schlage Fixes vor.
