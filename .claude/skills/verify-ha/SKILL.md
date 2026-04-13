---
name: verify-ha
description: "Prueft die laufende HA-Integration auf Fehler: HA-Logs, Entity-Status, Coordinator-Updates. Nutze diesen Skill um den aktuellen Zustand der HA-Integration zu diagnostizieren ohne neu zu deployen."
disable-model-invocation: true
---

# HA-Integration verifizieren

> **Umgebung:** Lokaler Kind-Cluster (Kubernetes in Docker), Skaffold-managed.
> HA laeuft als StatefulSet `homeassistant-0` im Namespace `default`.

## Schritt 1: Pod-Status pruefen

```bash
kubectl get pod homeassistant-0 -n default -o wide 2>&1
```

## Schritt 2: Aktuelle Kamerplanter-Logs

Zeige die letzten Kamerplanter-bezogenen Log-Eintraege:

```bash
kubectl logs homeassistant-0 -n default --since=5m 2>&1 | grep -iE "(kamerplanter|custom_components)" | tail -40
```

## Schritt 3: Fehler-Scan

Pruefe auf Fehler und Exceptions:

```bash
kubectl logs homeassistant-0 -n default --since=5m 2>&1 | grep -iE "(error|exception|traceback|warning)" | grep -iv "template" | tail -30
```

## Schritt 4: Integration-Status via API

Falls der Pod laeuft, pruefe den HA-Integrationsstatus:

```bash
kubectl exec homeassistant-0 -n default -- ls -la /config/custom_components/kamerplanter/ 2>&1
```

## Schritt 5: Ergebnis zusammenfassen

- **Pod-Status:** Running/NotRunning + Uptime
- **Integration geladen:** Ja/Nein (aus Logs)
- **Fehler:** Anzahl + Kategorisierung
- **Letzte Coordinator-Updates:** Timestamps falls sichtbar

Bei Fehlern: Analysiere die Ursache und schlage Fixes vor.
