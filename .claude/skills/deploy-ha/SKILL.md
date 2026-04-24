---
name: deploy-ha
description: "Deployed die HA-Integration in den lokalen Kubernetes-Cluster via Taskfile (lint, copy, restart, log-check). Nutze diesen Skill nach Aenderungen an custom_components/kamerplanter/ um die Integration schnell zu testen."
disable-model-invocation: true
---

# HA-Integration deployen und verifizieren

> **Umgebung:** Lokaler Kind-Cluster (Kubernetes in Docker), Skaffold-managed.
> HA laeuft als StatefulSet `homeassistant-0` im Namespace `default`.

## Ausfuehrung

Fuehre den Taskfile-Task aus:

```bash
task deploy-ha 2>&1; echo "EXIT:$?"
```

## Ergebnis melden

Stelle das Ergebnis in folgender Form dar:

```markdown
| Schritt            | Status     | Details                        |
|--------------------|------------|--------------------------------|
| Lint               | Pass/Fail  | {details}                      |
| Copy               | Pass/Fail  | kubectl cp                     |
| Cache Clear        | Pass/Fail  | __pycache__ entfernt           |
| HA Restart         | Pass/Fail  | kill 1 (Container-Restart)     |
| Container Ready    | Pass/Fail  | {time} bis Ready               |
| Integration Loaded | Pass/Fail  | Setup-Log-Eintraege            |
| Errors             | Pass/Fail  | {n} Fehler in Logs             |
```

### Bei Fehlern:

- Zeige die relevanten Log-Zeilen an
- Analysiere ob es ein Code-Fehler, Config-Problem oder Netzwerk-Issue ist
- Schlage einen konkreten Fix vor
- Frage ob der Fix angewendet und erneut deployed werden soll

### Bei Erfolg:

- Melde "HA-Integration erfolgreich deployed und gestartet"
- Zeige die geladenen Entities/Platforms falls in den Logs sichtbar
