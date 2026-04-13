# Installation

## Via HACS (empfohlen)

1. Oeffne **HACS** in Home Assistant
2. Klicke auf die drei Punkte (oben rechts) und waehle **Custom repositories**
3. Fuege `https://github.com/nolte/kamerplanter-ha` mit Kategorie **Integration** hinzu
4. Suche nach **Kamerplanter** und klicke **Download**
5. Starte Home Assistant neu

## Manuelle Installation

1. Lade die aktuelle Version von der [Releases-Seite](https://github.com/nolte/kamerplanter-ha/releases/latest) herunter
2. Entpacke und kopiere `custom_components/kamerplanter/` in dein HA `config/custom_components/`-Verzeichnis
3. Starte Home Assistant neu

## Voraussetzungen

- Home Assistant Core **2024.1** oder neuer
- Erreichbare Kamerplanter-Backend-Instanz
- Kamerplanter API-Key (`kp_`-Prefix) — optional im Light-Modus
