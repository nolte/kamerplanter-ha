# Fehlerbehebung

## Haeufige Fehler

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| "Kamerplanter nicht erreichbar" | Backend offline oder URL falsch | URL pruefen, Backend starten |
| "API-Key ungueltig" | Key revoked oder falsch | Neuen API-Key in Kamerplanter generieren, dann [Reauth](setup.md#reauth--reconfigure) |
| Entity zeigt "unavailable" | Coordinator-Update fehlgeschlagen | Logs pruefen, Polling-Intervall erhoehen |
| Integration laedt nicht | Verzeichnisstruktur falsch | Pfad pruefen: `custom_components/kamerplanter/manifest.json` |
| Entities fehlen nach Update | Cache veraltet | Service [`kamerplanter.clear_cache`](services.md#kamerplanterclear_cache) aufrufen |

---

## Diagnostics

Diagnostics-Daten sind verfuegbar unter **Einstellungen** > **Integrationen** > **Kamerplanter** > **Diagnostik**.

Die Diagnostics enthalten:

- **Konfiguration** — URL, Tenant (API-Keys werden automatisch maskiert)
- **Coordinator-Status** — letztes Update, Fehleranzahl, Polling-Intervall pro Coordinator
- **Entity-Uebersicht** — Anzahl pro Plattform (Sensor, Binary Sensor, Calendar, Todo, Button)

!!! tip "Bug-Reports"
    Bei Bug-Reports die Diagnostics-Datei anhaengen — sie enthaelt alle relevanten Infos ohne sensible Daten.

---

## Logs pruefen

=== "configuration.yaml"

    ```yaml
    logger:
      logs:
        custom_components.kamerplanter: debug
    ```

=== "HA-UI"

    **Einstellungen** > **System** > **Protokolle** und nach `kamerplanter` filtern.

!!! info "Debug-Logging deaktivieren"
    Debug-Logging erzeugt viele Log-Eintraege. Vergiss nicht, es nach der Fehlersuche wieder auf `info` oder `warning` zu setzen.
