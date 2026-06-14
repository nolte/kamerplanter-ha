# Installation

=== "HACS (Home Assistant Community Store) (empfohlen)"

    1. Öffne **HACS** in Home Assistant
    2. Klicke auf die drei Punkte (oben rechts) und wähle **Custom repositories**
    3. Füge `https://github.com/nolte/kamerplanter-ha` mit Kategorie **Integration** hinzu
    4. Suche nach **Kamerplanter** und klicke **Download**
    5. Starte Home Assistant neu

=== "Manuell"

    1. Lade die aktuelle Version von der [Releases-Seite](https://github.com/nolte/kamerplanter-ha/releases/latest) herunter
    2. Entpacke und kopiere `custom_components/kamerplanter/` in dein HA `config/custom_components/`-Verzeichnis
    3. Starte Home Assistant neu

    !!! warning "Verzeichnisstruktur beachten"
        Der Pfad muss exakt `config/custom_components/kamerplanter/manifest.json` sein. Lege ihn nicht in einem tieferen Unterverzeichnis ab.

!!! tip "Nach dem Neustart"
    Gehe zu **Einstellungen** > **Integrationen** > **Integration hinzufügen** und suche nach "Kamerplanter". Die Integration erscheint erst nach dem HA-Neustart.

## Voraussetzungen

| Anforderung | Details |
|-------------|---------|
| **Home Assistant** | Core **2024.1** oder neuer |
| **Backend** | Erreichbare Kamerplanter-Backend-Instanz |
| **API-Key** | `kp_`-Prefix — optional im Light-Modus |

:material-arrow-right: **Nächster Schritt:** [Einrichtung](setup.md) — Config Flow und Token-Austausch
