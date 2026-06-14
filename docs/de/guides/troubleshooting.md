# Fehlerbehebung

## Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|---------|
| "Kamerplanter nicht erreichbar" | Backend offline oder URL falsch | URL prüfen, Backend starten |
| "API-Key ungültig" | Key revoked oder falsch | Neuen API-Key in Kamerplanter generieren, dann [Reauth](setup.md#reauth-reconfigure) |
| Entity zeigt "unavailable" | Coordinator-Update fehlgeschlagen | Logs prüfen, Polling-Intervall erhöhen |
| Integration lädt nicht | Verzeichnisstruktur falsch | Pfad prüfen: `custom_components/kamerplanter/manifest.json` |
| Entities fehlen nach Update | Cache veraltet | Service [`kamerplanter.clear_cache`](services.md#kamerplanterclear_cache) aufrufen |

---

## Diagnostics

Diagnostics-Daten sind verfügbar unter **Einstellungen** > **Integrationen** > **Kamerplanter** > **Diagnostik**.

Die Diagnostics enthalten:

- **Konfiguration** — URL, Tenant (API-Keys werden automatisch maskiert)
- **Coordinator-Status** — letztes Update, Fehleranzahl, Polling-Intervall pro Coordinator
- **Entity-Übersicht** — Anzahl pro Plattform (Sensor, Binary Sensor, Calendar, Todo, Button)

!!! tip "Bug-Reports"
    Bei Bug-Reports die Diagnostics-Datei anhängen. Sie enthält alle relevanten Infos ohne sensible Daten.

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
    Debug-Logging erzeugt viele Log-Einträge. Vergiss nicht, es nach der Fehlersuche wieder auf `info` oder `warning` zu setzen.
