---
name: deploy-dev-ha
description: "Stellt eine wegwerfbare Dev-Home-Assistant-Instanz im lokalen Kind-Cluster bereit (StatefulSet homeassistant-0 + Service + PVC) via Taskfile. Nutze diesen Skill wenn kein HA-Pod im Cluster laeuft und `deploy-ha` mangels Ziel-Instanz fehlschlaegt — er schafft die Voraussetzung fuer den anschliessenden Code-Sync mit deploy-ha."
disable-model-invocation: true
---

# Dev-Home-Assistant im Cluster bereitstellen

> **Umgebung:** Lokaler Kind-Cluster (`kind-kamerplanter`), Namespace `default`.
> Erzeugt das StatefulSet `homeassistant` (Pod `homeassistant-0`, Label
> `app.kubernetes.io/name=homeassistant`) mit persistentem `/config`-PVC und
> einem ClusterIP-Service auf Port 8123. Manifest: `deploy/dev-homeassistant.yaml`.
>
> **Abgrenzung:** Dieser Skill bringt nur HA selbst hoch. Der Code-Sync der
> Integration laeuft danach ueber `deploy-ha` (kubectl cp). Onboarding (HA-User
> anlegen) erfolgt einmalig in der UI.

## Ausfuehrung

Fuehre den Taskfile-Task aus:

```bash
task deploy-dev-ha 2>&1; echo "EXIT:$?"
```

Der Task ist idempotent: ein erneuter Aufruf wendet das Manifest nur an
(`kubectl apply`) und laesst eine bereits laufende Instanz samt PVC unberuehrt.

## Ergebnis melden

Stelle das Ergebnis in folgender Form dar:

```markdown
| Schritt          | Status     | Details                                  |
|------------------|------------|------------------------------------------|
| Apply Manifest   | Pass/Fail  | StatefulSet + Service                     |
| Rollout Ready    | Pass/Fail  | {time} bis homeassistant-0 ready          |
| Prepare          | Pass/Fail  | /config/custom_components angelegt        |
| Info             | Pass/Fail  | Pod-Status + Zugriffshinweis              |
```

### Bei Fehlern:

- Zeige die relevanten kubectl-Ausgaben an.
- Haeufige Ursachen einordnen:
  - **Kein Cluster / falscher Kontext** → `kubectl config current-context` muss
    `kind-kamerplanter` sein.
  - **Rollout-Timeout** → Image-Pull (`ghcr.io/home-assistant/home-assistant:stable`)
    oder PVC-Binding (`kubectl describe pod homeassistant-0`).
- Schlage einen konkreten Fix vor und frage, ob er angewendet werden soll.

### Bei Erfolg:

- Melde "Dev-Home-Assistant erfolgreich bereitgestellt".
- Gib die naechsten Schritte aus:
  - **UI:** `kubectl port-forward -n default svc/homeassistant 8123:8123` → http://localhost:8123 (Onboarding durchfuehren).
  - **Integration deployen:** `/deploy-ha` bzw. `task deploy-ha`.
- Hinweis: Zum vollstaendigen Entfernen (inkl. PVC) `task deploy-dev-ha:teardown`.
- **NIEMALS** `kubectl delete pod homeassistant-0` zum Neustart — fuer einen
  Restart `kill 1` im Container nutzen (siehe deploy-ha), damit das `/config`-PVC
  und die kopierte Integration erhalten bleiben.
