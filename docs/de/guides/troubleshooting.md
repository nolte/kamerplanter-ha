---
title: Fehlerbehebung
audience:
  - self-hosting-admin
  - ha-end-users
content_mode: troubleshooting
track: user-docs
last_updated: 2026-06-24
---
# Fehlerbehebung

## Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|---------|
| "Kamerplanter nicht erreichbar" | Backend offline oder URL falsch | URL prüfen, Backend starten |
| "API-Key ungültig" | Key revoked oder falsch | Neuen API-Key in Kamerplanter generieren, dann [erneut authentifizieren](setup.md#erneute-authentifizierung-neukonfiguration) |
| Entity zeigt "unavailable" | Coordinator-Update fehlgeschlagen | Logs prüfen, Polling-Intervall erhöhen |
| Integration lädt nicht | Verzeichnisstruktur falsch | Pfad prüfen: `custom_components/kamerplanter/manifest.json` |
| Entities fehlen nach Update | Cache veraltet | Service [`kamerplanter.clear_cache`](services.md#kamerplanterclear_cache) aufrufen |

---

## Diagnostics

Die Diagnosedaten findest du unter **Einstellungen** > **Integrationen** > **Kamerplanter** > **Diagnostik**.

Die Diagnostics haben drei Teile:

- **Konfiguration:** die URL und der Tenant. API-Keys maskiert HA für dich.
- **Coordinator-Status:** das letzte Update, die Fehleranzahl und das Polling-Intervall. Jeder Coordinator bekommt eine eigene Zeile.
- **Entity-Übersicht:** wie viele Entities es pro Plattform gibt. Plattformen sind Sensor, Binary Sensor, Calendar, Todo und Button.

!!! tip "Bug-Reports"
    Hänge die Diagnostics-Datei an einen Bug-Report. Sie enthält alles Nötige, aber keine Geheimnisse.

---

## Logs prüfen

=== "configuration.yaml"

    ```yaml
    logger:
      logs:
        custom_components.kamerplanter: debug
    ```

=== "HA-UI"

    **Einstellungen** > **System** > **Protokolle** und nach `kamerplanter` filtern.

!!! info "Debug-Logging deaktivieren"
    Debug-Logging erzeugt viele Log-Einträge. Setze die Stufe nach der Fehlersuche wieder auf `info` oder `warning`.
