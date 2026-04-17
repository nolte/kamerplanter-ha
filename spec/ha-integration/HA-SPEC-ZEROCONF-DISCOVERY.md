# Spezifikation: mDNS/Zeroconf Auto-Discovery

```yaml
ID: HA-SPEC-ZEROCONF
Titel: Auto-Discovery des Kamerplanter Backends via mDNS/Zeroconf
Status: Spezifiziert
Version: 1.0
Datum: 2026-04-15
Behebt: -
Abhaengigkeiten: HA-SPEC-CONFIG (Config Flow muss bereits migriert sein)
Scope: manifest.json, config_flow.py, const.py, strings.json, translations/, Backend (python-zeroconf)
Style Guide: spec/style-guides/HA-INTEGRATION.md §8
```

---

## 1. Ziel

Kamerplanter-Backend-Instanzen sollen sich im lokalen Netzwerk per mDNS annoncieren, sodass Home Assistant sie automatisch erkennt und dem User zur Einrichtung vorschlaegt. Der manuelle Config Flow (`async_step_user`) bleibt als Fallback fuer nicht-lokale Instanzen bestehen.

---

## 2. Uebersicht

```
┌──────────────────────┐        mDNS Announcement         ┌──────────────────┐
│  Kamerplanter        │  _kamerplanter._tcp.local.        │  Home Assistant   │
│  Backend             │ ──────────────────────────────►   │  Zeroconf         │
│  (FastAPI + zeroconf)│  TXT: version, mode, tenant_slug  │  Listener         │
└──────────────────────┘                                   └────────┬─────────┘
                                                                    │
                                                           manifest.json match
                                                                    │
                                                                    ▼
                                                           ┌──────────────────┐
                                                           │  config_flow.py  │
                                                           │  async_step_     │
                                                           │  zeroconf()      │
                                                           └──────────────────┘
                                                                    │
                                                           Bestaetigung durch
                                                           User + API-Key
                                                                    │
                                                                    ▼
                                                           ┌──────────────────┐
                                                           │  ConfigEntry     │
                                                           │  wird erstellt   │
                                                           └──────────────────┘
```

---

## 3. mDNS Service-Definition

### 3.1 Service Type

```
_kamerplanter._tcp.local.
```

### 3.2 TXT-Records

Das Backend MUSS folgende TXT-Records im mDNS-Announcement mitliefern:

| Key | Pflicht | Beispiel | Beschreibung |
|-----|---------|----------|-------------|
| `version` | Ja | `0.8.2` | Backend-Version (Semver) |
| `mode` | Ja | `full` / `light` | Server-Modus (bestimmt ob API-Key noetig) |
| `api_path` | Ja | `/api` | API-Basispfad (fuer Reverse-Proxy-Szenarien) |
| `tenant` | Nein | `my-garden` | Tenant-Slug, falls Single-Tenant-Instanz |
| `instance_id` | Ja | `kp-abc123` | Eindeutige Instanz-ID (fuer Duplikat-Erkennung) |

### 3.3 Beispiel-Announcement

```
Service: Kamerplanter Backend
Type: _kamerplanter._tcp.local.
Host: kamerplanter-server.local
Port: 8000
TXT:
  version=0.8.2
  mode=full
  api_path=/api
  instance_id=kp-abc123
```

---

## 4. Backend-Seite: mDNS-Service registrieren

### 4.1 Dependency

```
python-zeroconf >= 0.131.0
```

### 4.2 Service-Registrierung (Lifecycle)

Das Backend registriert den mDNS-Service beim Start und deregistriert ihn beim Shutdown. Die Registrierung erfolgt als FastAPI Lifespan-Event.

```python
# backend: app/services/mdns.py

import socket
from zeroconf import ServiceInfo, Zeroconf


def create_service_info(
    *,
    port: int,
    version: str,
    mode: str,
    api_path: str = "/api",
    instance_id: str,
    tenant: str | None = None,
) -> ServiceInfo:
    """Create mDNS ServiceInfo for Kamerplanter backend."""
    properties: dict[str, str] = {
        "version": version,
        "mode": mode,
        "api_path": api_path,
        "instance_id": instance_id,
    }
    if tenant:
        properties["tenant"] = tenant

    hostname = socket.gethostname()

    return ServiceInfo(
        type_="_kamerplanter._tcp.local.",
        name=f"Kamerplanter ({hostname})._kamerplanter._tcp.local.",
        port=port,
        properties=properties,
        server=f"{hostname}.local.",
    )


class MdnsAnnouncer:
    """Manages mDNS service announcement lifecycle."""

    def __init__(self, service_info: ServiceInfo) -> None:
        self._info = service_info
        self._zeroconf: Zeroconf | None = None

    async def start(self) -> None:
        """Register mDNS service."""
        self._zeroconf = Zeroconf()
        self._zeroconf.register_service(self._info)

    async def stop(self) -> None:
        """Unregister mDNS service."""
        if self._zeroconf:
            self._zeroconf.unregister_service(self._info)
            self._zeroconf.close()
```

### 4.3 Lifespan-Integration

```python
# backend: app/main.py (Auszug)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... bestehender Startup-Code ...
    mdns = MdnsAnnouncer(create_service_info(
        port=settings.port,
        version=settings.version,
        mode=settings.server_mode,
        instance_id=settings.instance_id,
        tenant=settings.default_tenant if settings.single_tenant else None,
    ))
    await mdns.start()
    yield
    await mdns.stop()
```

### 4.4 Konfiguration

Die mDNS-Announcement MUSS per Konfiguration deaktivierbar sein (z.B. fuer Cloud-Deployments):

```env
KAMERPLANTER_MDNS_ENABLED=true    # default: true
KAMERPLANTER_INSTANCE_ID=kp-abc123  # auto-generiert falls leer
```

---

## 5. HA-Seite: manifest.json

### 5.1 Zeroconf-Eintrag hinzufuegen

```json
{
  "domain": "kamerplanter",
  "name": "Kamerplanter",
  "codeowners": ["@nolte"],
  "config_flow": true,
  "documentation": "https://github.com/nolte/kamerplanter-ha",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/nolte/kamerplanter-ha/issues",
  "integration_type": "hub",
  "loggers": ["custom_components.kamerplanter"],
  "requirements": [],
  "version": "0.1.0",
  "preload_platforms": false,
  "zeroconf": ["_kamerplanter._tcp.local."]
}
```

**Aenderungen gegenueber Ist-Zustand:**
- `"zeroconf": ["_kamerplanter._tcp.local."]` — Neu
- `"iot_class"`: `"cloud_polling"` → `"local_polling"` — Aenderung, da Discovery nur im lokalen Netz funktioniert

### 5.2 iot_class Entscheidung

| Szenario | iot_class | Begruendung |
|----------|-----------|-------------|
| Nur lokale Instanzen (mDNS) | `local_polling` | Backend laeuft im LAN |
| Gemischt (lokal + Cloud) | `local_polling` | Discovery impliziert lokales Primaer-Szenario |
| Nur Cloud (kein mDNS) | `cloud_polling` | Kein Discovery, nur manueller Flow |

Da mDNS per Definition lokal ist, wird `local_polling` als `iot_class` gesetzt. Nutzer, die eine Cloud-Instanz manuell konfigurieren, sind ein Sonderfall — `local_polling` ist trotzdem korrekt, da die Integration primaer fuer lokale Nutzung vorgesehen ist.

---

## 6. HA-Seite: Config Flow Erweiterung

### 6.1 Neuer Discovery Step

```python
# config_flow.py

from homeassistant.components.zeroconf import ZeroconfServiceInfo

class KamerplanterConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str = ""
        self._api_key: str | None = None
        self._light_mode: bool = False
        self._server_version: str = ""
        self._tenants: list[dict[str, Any]] = []
        # ★ Neu: Discovery-Daten
        self._discovery_info: ZeroconfServiceInfo | None = None
        self._instance_id: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle mDNS/Zeroconf discovery of a Kamerplanter backend."""
        properties = discovery_info.properties

        # Extrahiere TXT-Records
        instance_id = properties.get("instance_id", "")
        version = properties.get("version", "unknown")
        mode = properties.get("mode", "full")
        api_path = properties.get("api_path", "/api")
        tenant = properties.get("tenant")

        if not instance_id:
            return self.async_abort(reason="missing_instance_id")

        # Duplikat-Pruefung ueber instance_id + tenant
        unique_suffix = f"{instance_id}_{tenant}" if tenant else instance_id
        await self.async_set_unique_id(unique_suffix)
        self._abort_if_unique_id_configured(
            updates={CONF_URL: self._build_url(discovery_info, api_path)}
        )

        # URL aus Discovery-Info zusammenbauen
        self._base_url = self._build_url(discovery_info, api_path)
        self._server_version = version
        self._light_mode = mode == "light"
        self._discovery_info = discovery_info
        self._instance_id = instance_id

        # Platzhalter-Titel fuer die Discovery-Notification
        self.context["title_placeholders"] = {
            "name": discovery_info.name.split(".")[0],
            "host": discovery_info.host or "unknown",
        }

        # Health-Check: Backend erreichbar?
        session = async_get_clientsession(self.hass)
        api_no_auth = KamerplanterApi(base_url=self._base_url, session=session)
        try:
            await api_no_auth.async_get_health()
        except KamerplanterConnectionError:
            return self.async_abort(reason="cannot_connect")

        # Single-Tenant aus TXT? Dann Bestaetigung zeigen
        if tenant:
            self._tenants = [{"slug": tenant, "name": tenant}]

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered Kamerplanter instance and collect API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input.get(CONF_API_KEY) or None

            # API-Key-Validierung (ausser im Light-Mode)
            if not self._light_mode:
                if not self._api_key:
                    errors["base"] = "invalid_auth"
                    return self.async_show_form(
                        step_id="discovery_confirm",
                        data_schema=self._discovery_confirm_schema(),
                        description_placeholders=self._discovery_placeholders(),
                        errors=errors,
                    )
                session = async_get_clientsession(self.hass)
                api = KamerplanterApi(
                    base_url=self._base_url,
                    session=session,
                    api_key=self._api_key,
                )
                try:
                    await api.async_get_current_user()
                except KamerplanterAuthError:
                    errors["base"] = "invalid_auth"
                    return self.async_show_form(
                        step_id="discovery_confirm",
                        data_schema=self._discovery_confirm_schema(),
                        description_placeholders=self._discovery_placeholders(),
                        errors=errors,
                    )

            # Tenant-Abfrage wenn noetig
            if not self._tenants:
                session = async_get_clientsession(self.hass)
                api = KamerplanterApi(
                    base_url=self._base_url,
                    session=session,
                    api_key=self._api_key,
                )
                try:
                    self._tenants = await api.async_get_tenants()
                except KamerplanterConnectionError:
                    errors["base"] = "cannot_connect"
                    return self.async_show_form(
                        step_id="discovery_confirm",
                        data_schema=self._discovery_confirm_schema(),
                        description_placeholders=self._discovery_placeholders(),
                        errors=errors,
                    )

                if not self._tenants:
                    return self.async_abort(reason="no_tenants")

                if len(self._tenants) > 1:
                    return await self.async_step_tenant()

            # Single-Tenant oder aus TXT-Record
            tenant_slug = self._tenants[0]["slug"]
            await self.async_set_unique_id(
                f"{self._instance_id}_{tenant_slug}"
            )
            self._abort_if_unique_id_configured()
            return self._create_entry(tenant_slug=tenant_slug)

        # Formular anzeigen
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=self._discovery_confirm_schema(),
            description_placeholders=self._discovery_placeholders(),
        )

    # --- Helpers ---

    @staticmethod
    def _build_url(
        discovery_info: ZeroconfServiceInfo, api_path: str
    ) -> str:
        """Build base URL from Zeroconf discovery info."""
        host = discovery_info.host
        port = discovery_info.port
        # IPv6-Adressen in Klammern
        if host and ":" in host:
            host = f"[{host}]"
        return f"http://{host}:{port}"

    def _discovery_confirm_schema(self) -> vol.Schema:
        """Schema for discovery confirmation (API key only)."""
        if self._light_mode:
            return vol.Schema({})
        return vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
            }
        )

    def _discovery_placeholders(self) -> dict[str, str]:
        """Placeholders for discovery confirmation description."""
        return {
            "url": self._base_url,
            "version": self._server_version,
            "mode": "Light" if self._light_mode else "Full",
        }
```

### 6.2 Unique-ID-Schema

Discovery-basierte Eintraege verwenden `instance_id` statt URL als Basis fuer die Unique ID. Dies hat den Vorteil, dass sich die URL aendern kann (z.B. DHCP-Lease-Wechsel) ohne dass ein Duplikat entsteht.

| Quelle | Unique ID Format | Beispiel |
|--------|-----------------|----------|
| Manuell (`async_step_user`) | `{base_url}_{tenant_slug}` | `http://192.168.1.50:8000_my-garden` |
| Discovery (`async_step_zeroconf`) | `{instance_id}_{tenant_slug}` | `kp-abc123_my-garden` |

`_abort_if_unique_id_configured(updates=...)` sorgt dafuer, dass bei IP-Aenderung die bestehende Config Entry automatisch aktualisiert wird statt einen Duplikat-Fehler zu erzeugen.

---

## 7. HA-Seite: strings.json Erweiterung

```json
{
  "config": {
    "flow_title": "Kamerplanter ({name})",
    "step": {
      "discovery_confirm": {
        "title": "Kamerplanter discovered",
        "description": "A Kamerplanter backend was found at **{url}** (version {version}, mode: {mode}).\n\nDo you want to set up this instance?",
        "data": {
          "api_key": "API Key (kp_...)"
        }
      }
    },
    "abort": {
      "missing_instance_id": "The discovered service is missing a required instance ID",
      "already_configured": "This Kamerplanter instance is already configured"
    }
  }
}
```

**Hinweis:** Die bestehenden Step-Eintraege (`user`, `tenant`, `reauth_confirm`, `reconfigure`) bleiben unveraendert. Nur `discovery_confirm` und die neuen Abort-Reasons werden hinzugefuegt.

---

## 8. HA-Seite: const.py Erweiterung

```python
# Zeroconf / Discovery
MDNS_SERVICE_TYPE = "_kamerplanter._tcp.local."
CONF_INSTANCE_ID = "instance_id"
```

`CONF_INSTANCE_ID` wird in `config_entry.data` gespeichert, damit spaetere Flows (Reauth, Reconfigure) die Instanz-ID kennen.

### 8.1 _create_entry Anpassung

```python
def _create_entry(self, tenant_slug: str | None = None) -> ConfigFlowResult:
    title = "Kamerplanter"
    if tenant_slug:
        title = f"Kamerplanter ({tenant_slug})"

    data: dict[str, Any] = {
        CONF_URL: self._base_url,
        CONF_LIGHT_MODE: self._light_mode,
    }
    if self._api_key:
        data[CONF_API_KEY] = self._api_key
    if tenant_slug:
        data[CONF_TENANT_SLUG] = tenant_slug
    # ★ Neu: instance_id bei Discovery-basierter Einrichtung
    if self._instance_id:
        data[CONF_INSTANCE_ID] = self._instance_id

    return self.async_create_entry(title=title, data=data)
```

---

## 9. IP-Aenderungs-Handling

Wenn ein bereits konfiguriertes Backend eine neue IP bekommt (DHCP-Lease-Wechsel, Neustart), sendet es ein neues mDNS-Announcement. HA ruft erneut `async_step_zeroconf` auf.

Durch `_abort_if_unique_id_configured(updates={CONF_URL: new_url})` passiert Folgendes:

1. HA erkennt die bekannte `instance_id` (Unique ID)
2. Die bestehende Config Entry wird mit der neuen URL aktualisiert
3. Der Flow wird abgebrochen (kein neuer Eintrag)
4. Die Integration wird automatisch neu geladen

**Kein manuelles Reconfigure noetig bei IP-Aenderung.**

---

## 10. Sicherheit

### 10.1 API-Key wird NICHT per mDNS uebertragen

Der API-Key wird ausschliesslich im Config Flow ueber die HA-UI eingegeben. mDNS-TXT-Records enthalten niemals Credentials.

### 10.2 Health-Check vor Bestaetigung

Bevor der User den Discovery-Dialog sieht, wird ein Health-Check durchgefuehrt. Ist das Backend nicht erreichbar (z.B. kurzzeitiger mDNS-Cache), wird der Flow abgebrochen.

### 10.3 Instance-ID Validierung

Ohne `instance_id` im TXT-Record wird der Discovery-Flow sofort abgebrochen (`missing_instance_id`). Dies verhindert, dass fremde Services mit demselben Service-Type faelschlicherweise als Kamerplanter erkannt werden.

---

## 11. Testszenarien

### 11.1 Unit Tests (config_flow)

| Test | Beschreibung |
|------|-------------|
| `test_zeroconf_discovery_full_mode` | Discovery mit mode=full, User gibt API-Key ein, Entry wird erstellt |
| `test_zeroconf_discovery_light_mode` | Discovery mit mode=light, kein API-Key noetig, Entry wird erstellt |
| `test_zeroconf_discovery_single_tenant` | tenant im TXT-Record, kein Tenant-Step noetig |
| `test_zeroconf_discovery_multi_tenant` | Kein tenant im TXT-Record, Tenant-Step wird angezeigt |
| `test_zeroconf_discovery_duplicate` | Bereits konfigurierte instance_id → abort |
| `test_zeroconf_discovery_ip_update` | Bekannte instance_id mit neuer IP → URL-Update auf bestehender Entry |
| `test_zeroconf_discovery_unreachable` | Health-Check schlaegt fehl → abort(cannot_connect) |
| `test_zeroconf_discovery_missing_instance_id` | Kein instance_id im TXT → abort(missing_instance_id) |
| `test_zeroconf_discovery_invalid_auth` | Falscher API-Key → Fehler, erneute Eingabe |
| `test_manual_flow_still_works` | `async_step_user` funktioniert weiterhin ohne Discovery |

### 11.2 Integrationstests (Backend)

| Test | Beschreibung |
|------|-------------|
| `test_mdns_service_registered_on_startup` | Service wird beim Start registriert |
| `test_mdns_service_unregistered_on_shutdown` | Service wird beim Shutdown deregistriert |
| `test_mdns_disabled_by_config` | `MDNS_ENABLED=false` → kein Service registriert |
| `test_mdns_txt_records_complete` | Alle Pflicht-TXT-Records vorhanden |

---

## 12. Umsetzungsreihenfolge

### Phase 1: Backend (Kamerplanter-Repository)

1. `python-zeroconf` als optionale Dependency hinzufuegen
2. `app/services/mdns.py` implementieren (MdnsAnnouncer, create_service_info)
3. Lifespan-Integration in `app/main.py`
4. Konfiguration: `MDNS_ENABLED`, `INSTANCE_ID` in Settings
5. Tests fuer mDNS-Registrierung/Deregistrierung

### Phase 2: HA-Integration (dieses Repository)

6. `const.py`: `MDNS_SERVICE_TYPE`, `CONF_INSTANCE_ID` hinzufuegen
7. `manifest.json`: `zeroconf` und `iot_class` aktualisieren
8. `config_flow.py`: `async_step_zeroconf`, `async_step_discovery_confirm` implementieren
9. `config_flow.py`: `_create_entry` um `instance_id` erweitern
10. `strings.json` + `translations/`: Discovery-Texte hinzufuegen
11. Tests fuer alle Discovery-Szenarien

---

## 13. Akzeptanzkriterien

- [ ] Backend annonciert `_kamerplanter._tcp.local.` per mDNS beim Start
- [ ] Backend deregistriert den Service sauber beim Shutdown
- [ ] mDNS kann per Config deaktiviert werden
- [ ] TXT-Records enthalten version, mode, api_path, instance_id
- [ ] HA erkennt den Service automatisch und zeigt Discovery-Dialog
- [ ] Discovery-Dialog zeigt URL, Version und Modus des Backends
- [ ] API-Key-Eingabe im Discovery-Dialog (nur im Full-Mode)
- [ ] Tenant-Auswahl im Discovery-Dialog (nur bei Multi-Tenant)
- [ ] Bereits konfigurierte Instanzen werden nicht erneut angeboten
- [ ] IP-Aenderung einer bekannten Instanz aktualisiert die bestehende Config Entry
- [ ] Manueller Config Flow (`async_step_user`) funktioniert weiterhin
- [ ] Alle Unit Tests bestanden
