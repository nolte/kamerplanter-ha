# Fehlerbehebung

## Haeufige Fehler

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| "Kamerplanter nicht erreichbar" | Backend offline oder URL falsch | URL pruefen, Backend starten |
| "API-Key ungueltig" | Key revoked oder falsch | Neuen API-Key in Kamerplanter generieren |
| Entity zeigt "unavailable" | Coordinator-Update fehlgeschlagen | Logs pruefen, Polling-Intervall erhoehen |

## Diagnostics

Diagnostics-Daten sind verfuegbar unter **Einstellungen** > **Integrationen** > **Kamerplanter** > **Diagnostik**.

Die Diagnostics enthalten:

- Konfigurationsdaten (URL, Tenant — API-Keys werden automatisch maskiert)
- Coordinator-Status (letztes Update, Fehleranzahl)
- Entity-Uebersicht (Anzahl pro Plattform)

## Logs pruefen

HA-Logs fuer die Integration filtern:

```yaml
# In configuration.yaml
logger:
  logs:
    custom_components.kamerplanter: debug
```

Oder in der HA-UI: **Einstellungen** > **System** > **Protokolle** und nach "kamerplanter" filtern.
