# Spezifikation: HACS ZIP-Release-Distribution

```yaml
ID: HA-SPEC-HACS-RELEASE
Titel: HACS ZIP-Release-Asset-Distribution (zip_release / filename / content_in_root)
Status: Spezifiziert
Version: 1.0
Datum: 2026-06-25
Behebt: #35
Abhaengigkeiten: HA-CUSTOM-INTEGRATION (manifest.json/domain), release-automation (gh-plumbing)
Scope: hacs.json, .github/workflows/release-publish.yml
Quellen:
  - HACS Source: hacs/integration custom_components/hacs/repositories/base.py (zip_release-Pfad)
  - HACS Docs: hacs.xyz/docs/publish/start (hacs.json-Keys)
  - Praezedenz: alandtse/alexa_media_player (hacs.json)
  - Reusable: nolte/gh-plumbing reusable-release-publish.yml @v1.1.25
  - Upstream-Spec (ausstehend): nolte/gh-plumbing#377 (spec/ha/hacs-release)
```

## Kontext

Eine HACS-Integration kann auf zwei Wegen installiert werden:

1. **git-source (Default):** HACS klont den Quellbaum des Release-Tags und installiert
   aus `custom_components/<domain>/`. `hacs.json` deklariert **kein** `filename`.
2. **zip-release:** HACS lädt ein benanntes ZIP-Asset vom GitHub-Release herunter und
   entpackt es. Aktiviert durch `zip_release: true` + `filename` in `hacs.json`.

Diese Integration nutzt den von `nolte/gh-plumbing` bereitgestellten
`reusable-release-publish.yml`-Workflow. Dieser **baut beim Publish ein ZIP-Asset
und hängt es an den Release** (Schritt „Attach HACS zip-release asset"), bevor der
Draft auf `published` geflippt wird. Damit HACS dieses Asset auch wirklich nutzt
(statt git-source), muss `hacs.json` den zip-release-Vertrag erfüllen. Diese Spec
hält den verbindlichen Vertrag und seine Herleitung fest.

## Die verbindliche Konfiguration

### `hacs.json`

```json
{
  "name": "Kamerplanter",
  "render_readme": true,
  "content_in_root": false,
  "zip_release": true,
  "filename": "kamerplanter.zip",
  "homeassistant": "2024.1.0"
}
```

- **`zip_release: true`** — aktiviert den ZIP-Release-Pfad. Laut HACS-Doku nur für
  Integrationen unterstützt und **erfordert** `filename`.
- **`filename: "kamerplanter.zip"`** — der Asset-Name, den HACS am Release sucht und
  herunterlädt. **Muss exakt** dem Asset-Namen entsprechen, den der Reusable baut
  (siehe `asset-filename` unten).
- **`content_in_root: false`** — beschreibt das **Repo**-Layout (Integration liegt
  unter `custom_components/<domain>/`, nicht im Repo-Root). Für den zip-release-Pfad
  ist der Wert **irrelevant** (siehe „Verhalten von HACS"), `false` ist der korrekte,
  neutrale Wert.

### `.github/workflows/release-publish.yml` (Caller)

```yaml
with:
  asset-filename: kamerplanter.zip   # Build-Name; MUSS hacs.json `filename` gleichen
```

Ab `gh-plumbing` **v1.1.25** akzeptiert der Reusable den Input `asset-filename`. Er
definiert den **Build-Namen** des Assets beim Consumer (Trennung: Logik im Reusable,
Artefakt-Definition beim Nutzer). Ohne den Input fällt der Reusable auf
`hacs.json .filename` und schließlich auf `<domain>.zip` zurück.

> **Invariante:** `asset-filename` (Build-Name) und `hacs.json` `filename`
> (HACS-Such-Name) **müssen identisch** sein. Eine Abweichung bedeutet: HACS sucht
> ein Asset, das der Reusable nie gebaut hat → Installation schlägt fehl.

## Verhalten von HACS (maßgeblich aus dem Source)

Im zip-release-Pfad (`hacs/integration`, `repositories/base.py`) macht HACS:

```python
with zipfile.ZipFile(temp_file, "r") as zip_file:
    zip_file.extractall(self.content.path.local)   # = custom_components/<domain>/
```

Daraus folgt der **load-bearing**-Teil des Vertrags:

- HACS entpackt das Asset **direkt** nach `custom_components/<domain>/`.
- Das ZIP **muss die Integrationsdateien im Wurzelverzeichnis** enthalten
  (`manifest.json`, `__init__.py`, … im ZIP-Root) — exakt das Layout, das der
  `reusable-release-publish.yml` baut (Inhalt von `custom_components/<domain>/` im
  ZIP-Root, „integration_blueprint"-Muster).
- **`content_in_root` wird im zip-release-Pfad nicht ausgewertet.** Es greift nur im
  Nicht-ZIP-/Single-File-Pfad (Plugin/Theme).

**Produktionspräzedenz:** `alandtse/alexa_media_player` shippt die identische Form
(`zip_release: true` + `filename` + `content_in_root: false`).

## Wann ist diese Konfiguration relevant?

Die Konfiguration wirkt an drei klar getrennten Zeitpunkten im Release-/
Entwicklungsprozess:

### 1. Release-Zeit — Asset-Bau (Maintainer/CI)
Beim Dispatch von `release-publish.yml` baut der Reusable das ZIP und hängt es an
den Draft, **bevor** auf `published` geflippt wird. Relevant ist hier:
- `asset-filename` im Caller bestimmt den Build-Namen.
- Das ZIP-Layout (Inhalt im Root) ist durch den Reusable fix vorgegeben.
- Verifizierbar via `dry_run=true` (baut, lädt aber nicht hoch) und nach dem Publish
  über `gh release view <tag> --json assets` (genau **ein** `kamerplanter.zip`).

### 2. Install-/Update-Zeit — HACS beim Endnutzer
Wenn ein Nutzer die Integration über HACS installiert oder aktualisiert, liest HACS
`hacs.json` des Release-Tags und entscheidet **anhand von `zip_release`+`filename`**,
ob es das Asset lädt (zip-release) oder den git-source-Klon nutzt. Relevant:
- Fehlt `filename`/`zip_release` → HACS ignoriert das Asset und nimmt git-source.
- Namens-Mismatch → Download-/Installationsfehler.

### 3. Entwicklungs-Zeit — Änderungen, die den Vertrag berühren
Diese Spec ist Pflichtlektüre, sobald eines davon geändert wird:
- **`hacs.json`** (`filename`, `zip_release`, `content_in_root`, `name`/`domain`).
- **`asset-filename`** im Caller oder der **Domain** (`manifest.json` `domain`), da
  der Default-Asset-Name `<domain>.zip` ist.
- **Bump des `gh-plumbing`-Pins** in `release-publish.yml` — der `asset-filename`-Input
  existiert erst ab **v1.1.25**; ältere Pins lesen nur `hacs.json .filename`.
- **Umstieg git-source ↔ zip-release** — ein Wechsel ändert den Installationspfad für
  bestehende Nutzer und MUSS mit einer echten HACS-Installation validiert werden.

## Anti-Patterns / Stolpersteine

- **Zwei ZIP-Assets am Release.** Ein projekt-spezifischer `release.yml`-Workflow,
  der zusätzlich auf `release: published` ein eigenes ZIP baut, erzeugt ein zweites,
  abweichend benanntes Asset. Der Reusable besitzt das Packaging — ein solcher
  Workflow ist redundant und wird entfernt (vgl. #35).
- **`content_in_root: true` für eine Integration unter `custom_components/`.** Falsch
  für das Repo-Layout; im zip-release-Pfad ohnehin wirkungslos.
- **`asset-filename` ≠ `hacs.json filename`.** Bricht die Installation (siehe Invariante).

## Acceptance Criteria

- [ ] `hacs.json` enthält `zip_release: true` und `filename`, und `filename` entspricht
      `asset-filename` im Caller.
- [ ] `release-publish.yml` pinnt `gh-plumbing` auf **≥ v1.1.25** und übergibt
      `asset-filename`.
- [ ] Pro veröffentlichtem Release existiert **genau ein** ZIP-Asset mit diesem Namen.
- [ ] Der Umstieg auf zip-release ist mit einer echten HACS-Installation aus einem
      veröffentlichten Release validiert (erstmals geplant für v0.1.6).
- [ ] Kein projekt-spezifischer Release-Workflow baut ein konkurrierendes ZIP.

## Verweise

- Upstream-Vertrag (ausstehend): `nolte/gh-plumbing#377` — kanonische
  `spec/ha/hacs-release` im Reusable-Repo. Diese Spec spiegelt den Vertrag
  consumer-seitig und sollte bei Veröffentlichung der Upstream-Spec darauf verweisen.
- `HA-CUSTOM-INTEGRATION.md` — `manifest.json`, `domain`.
