---
title: Lovelace Custom Cards
audience:
  - ha-end-users
content_mode: how-to
track: user-docs
last_updated: 2026-06-27
---
# Lovelace Custom Cards

Die Integration liefert 5 Custom Lovelace Cards mit. Sie registriert die Cards beim Setup für dich. Du legst keine Ressource von Hand an.

| Card | Beschreibung |
|------|-------------|
| `kamerplanter-plant-card` | Pflanzen-Übersicht mit Phasen-Timeline und Sollwerten |
| `kamerplanter-mix-card` | Nährstoff-Dosierung pro Kanal visualisiert |
| `kamerplanter-tank-card` | Tank-Status mit Füllstand und Lösungsalter |
| `kamerplanter-care-card` | Pflege-Erinnerungen mit Bestätigen/Überspringen |
| `kamerplanter-houseplant-card` | Vereinfachte Card für Zimmerpflanzen |

!!! info "Auto-Registrierung"
    Die Integration lädt die Cards aus ihrem `www/`-Verzeichnis. Du fügst sie nicht von Hand als Lovelace-Ressource hinzu.

## Konfiguration

Konfiguriere alle Cards über den Standard-HA-Editor. Du wählst die Entity im Editor aus, YAML ist also nicht nötig.

=== "Plant Card"

    Zeigt die aktuelle Phase, Tage in Phase und den Phasenverlauf.

    ```yaml
    type: custom:kamerplanter-plant-card
    entity: sensor.kp_northern_lights_phase
    ```

=== "Mix Card"

    Visualisiert die Dünger-Dosierung pro Kanal mit Mengenangaben in ml/L.

    ```yaml
    type: custom:kamerplanter-mix-card
    entity: sensor.kp_12345_giesswasser_mix
    ```

=== "Tank Card"

    Zeigt Füllstand, Volumen und Lösungsalter des Tanks.

    ```yaml
    type: custom:kamerplanter-tank-card
    entity: sensor.kp_90639_info
    ```

=== "Care Card"

    Listet fällige Pflege-Aufgaben mit Bestätigen/Überspringen-Buttons.

    ```yaml
    type: custom:kamerplanter-care-card
    entity: binary_sensor.kp_care_overdue
    ```

=== "Houseplant Card"

    Vereinfachte Darstellung für Zimmerpflanzen ohne komplexe Nährstoffdaten.

    ```yaml
    type: custom:kamerplanter-houseplant-card
    entity: sensor.kp_monstera_phase
    ```

## Fehlerbehebung

### Cards erscheinen nicht im Card-Picker

Die Integration registriert die Cards beim Setup automatisch. Tauchen sie trotzdem nicht in der Auswahl auf, hat dein Browser die Card-Liste geladen, **bevor** die Registrierung abgeschlossen war — die Cards selbst sind in Ordnung.

1. Lade die Seite hart neu: `Strg + Shift + R` (macOS: `Cmd + Shift + R`).
2. Hilft das nicht, leere den Browser-Cache für deine HA-Adresse.
3. In der **Begleit-App** (Android/iOS): `Einstellungen → Companion-App → Frontend-Cache leeren`, danach App neu starten.

!!! tip "Sofort-Workaround"
    Du kannst jede Card auch ohne Picker hinzufügen: `Karte hinzufügen → Manuell` und z. B. `type: custom:kamerplanter-plant-card` eintragen.

### Prüfen, ob die Cards geladen sind

Öffne auf der HA-Seite die Browser-Konsole (`F12`) und gib ein:

```js
window.customCards
```

- Enthält die Ausgabe `kamerplanter-*`-Einträge, war es nur der Cache — nach dem Reload erscheinen sie im Picker.
- Ist die Liste leer oder ohne `kamerplanter`-Einträge, prüfe im **Network-Tab**, ob die `/kamerplanter/...js`-Dateien mit Status 200 geladen werden, und im **Console-Tab** auf rote Fehlermeldungen beim Laden.

### Ressourcen kontrollieren

Unter `Einstellungen → Dashboards → ⋮ → Ressourcen` müssen fünf Einträge mit der URL `/kamerplanter/...js` und Typ `JavaScript-Modul` stehen. Fehlen sie, lade die Integration neu (`Einstellungen → Geräte & Dienste → Kamerplanter → ⋮ → Neu laden`).

!!! note "YAML-Modus"
    Läuft dein Lovelace im YAML-Modus (`lovelace: mode: yaml` in der `configuration.yaml`), kann die Integration die Ressourcen nicht automatisch eintragen. Füge sie dann selbst hinzu:

    ```yaml
    lovelace:
      mode: yaml
      resources:
        - url: /kamerplanter/kamerplanter-plant-card.js
          type: module
        - url: /kamerplanter/kamerplanter-mix-card.js
          type: module
        - url: /kamerplanter/kamerplanter-tank-card.js
          type: module
        - url: /kamerplanter/kamerplanter-care-card.js
          type: module
        - url: /kamerplanter/kamerplanter-houseplant-card.js
          type: module
    ```
