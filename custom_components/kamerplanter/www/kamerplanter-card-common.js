/**
 * kamerplanter-card-common.js
 *
 * Gemeinsames ES-Modul fuer alle Kamerplanter Lovelace Cards. Konsolidiert
 * bislang je Card duplizierten Code:
 *   - HTML/Attribut-Escaping (escapeHtml / escapeAttr / safeNum / capitalize)
 *   - Verfuegbarkeits-Checks (isUnavailableState / isUnavailable)
 *   - Kami-Phase-Maps + Label-/SVG-Aufloesung (KAMI_PHASE_SVG / PHASE_LABELS)
 *   - ha-form-Ready-Singleton (haFormReady)
 *   - Editor-Basisklasse (KamerplanterCardEditor)
 *   - Device-Entity-Aufloesung (getEntityMap / getDeviceName)
 *   - i18n-Utility (pickLang / t) — Kataloge liefert WP-16 pro Card
 *
 * Auslieferung: Das Modul wird als statische Datei unter
 * ``/kamerplanter/kamerplanter-card-common.js`` bereitgestellt und von den
 * Cards per relativem Import (``./kamerplanter-card-common.js``) geladen. Es
 * ist KEINE Card und wird daher NICHT als Lovelace-Resource registriert.
 */

/* ================================================================== *
 *  HTML / Attribut Escaping                                           *
 * ================================================================== */

/**
 * Escape a value for safe use in HTML text context. Uses the DOM to encode
 * &, < and > entities (text-node semantics).
 */
export function escapeHtml(s) {
  const el = document.createElement("span");
  el.textContent = s == null ? "" : String(s);
  return el.innerHTML;
}

/**
 * Escape a value for safe use inside a double/single quoted HTML attribute.
 * Extends escapeHtml by additionally encoding " and ' so backend-provided
 * strings cannot break out of the attribute (or break querySelector calls).
 */
export function escapeAttr(s) {
  return escapeHtml(s).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/**
 * Coerce a backend value to a safe string for HTML text content. Finite
 * numbers are rendered as-is; anything else is HTML-escaped so malicious
 * backend payloads cannot inject markup.
 */
export function safeNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? String(n) : escapeHtml(String(v));
}

/** Capitalize the first character of a string; "" for a falsy input. */
export function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
}

/* ================================================================== *
 *  Availability helpers                                               *
 * ================================================================== */

/**
 * True for a raw state *value* that carries no usable reading. Covers missing
 * states (null/undefined) and the HA sentinels "unknown"/"unavailable".
 */
export function isUnavailableState(state) {
  return state == null || state === "unavailable" || state === "unknown";
}

/**
 * True when a state *object* is missing or reports "unavailable"/"unknown".
 * Such states must never be rendered as a real value / success case.
 */
export function isUnavailable(stateObj) {
  return (
    !stateObj ||
    stateObj.state === "unavailable" ||
    stateObj.state === "unknown"
  );
}

/* ================================================================== *
 *  Kami phase maps                                                     *
 * ================================================================== */

// Konsolidierte Union der frueher zwischen plant-card (KAMI_PHASE_SVG) und
// houseplant-card (KAMI_PHASE_SVG_HP) divergierenden Maps. Beide SVG-Maps
// waren deckungsgleich; die Label-Maps unterschieden sich nur in der
// Umlaut-Kodierung — hier die korrekte UTF-8-Variante.
export const KAMI_PHASE_SVG = {
  germination:         "/local/kami/timeline-kami-phase-germination.svg",
  seedling:            "/local/kami/timeline-kami-phase-seedling.svg",
  vegetative:          "/local/kami/timeline-kami-phase-vegetative.svg",
  flowering:           "/local/kami/timeline-kami-phase-flowering.svg",
  ripening:            "/local/kami/timeline-kami-phase-ripening.svg",
  harvest:             "/local/kami/timeline-kami-phase-harvest.svg",
  dormancy:            "/local/kami/timeline-kami-phase-dormancy.svg",
  juvenile:            "/local/kami/timeline-kami-phase-juvenile.svg",
  climbing:            "/local/kami/timeline-kami-phase-climbing.svg",
  mature:              "/local/kami/timeline-kami-phase-mature.svg",
  senescence:          "/local/kami/timeline-kami-phase-senescence.svg",
  flushing:            "/local/kami/timeline-kami-phase-flushing.svg",
  leaf_phase:          "/local/kami/timeline-kami-phase-leaf-phase.svg",
  short_day_induction: "/local/kami/timeline-kami-phase-short-day-induction.svg",
};

export const PHASE_LABELS = {
  germination:         "Keimung",
  seedling:            "Sämling",
  vegetative:          "Vegetativ",
  flowering:           "Blüte",
  ripening:            "Reife",
  harvest:             "Ernte",
  dormancy:            "Ruhephase",
  flush:               "Spülphase",
  flushing:            "Spülung",
  drying:              "Trocknung",
  curing:              "Curing",
  leaf_phase:          "Blattphase",
  short_day_induction: "Kurztageinleitung",
  juvenile:            "Juvenil",
  climbing:            "Kletterphase",
  mature:              "Reifephase",
  senescence:          "Seneszenz",
};

/** Resolve the Kami SVG URL for a phase, or null when unknown. */
export function kamiSvg(phase) {
  return KAMI_PHASE_SVG[(phase || "").toLowerCase()] || null;
}

/** Human-readable phase label; em-dash for an empty phase. */
export function phaseLabel(phase) {
  const key = (phase || "").toLowerCase();
  return PHASE_LABELS[key] || (phase ? capitalize(phase) : "—");
}

/* ================================================================== *
 *  ha-form ready singleton                                            *
 * ================================================================== */

let _haFormReadyPromise;

/**
 * Resolve once ``ha-form`` is defined. ha-form transitively loads
 * ha-selector-entity → ha-entity-picker, so editors that build entity
 * selectors only need to await this (UI-NFR-015 §2.2). The promise is created
 * lazily and cached so all cards share a single warm-up.
 */
export function haFormReady() {
  if (!_haFormReadyPromise) {
    _haFormReadyPromise = (async () => {
      if (customElements.get("ha-form")) return;
      await customElements.whenDefined("hui-entities-card");
      const helpers = await window.loadCardHelpers?.();
      if (helpers) {
        const temp = await helpers.createCardElement({
          type: "entities",
          entities: [],
        });
        if (temp?.constructor?.getConfigElement) {
          await temp.constructor.getConfigElement();
        }
      }
      await customElements.whenDefined("ha-form");
    })();
  }
  return _haFormReadyPromise;
}

/* ================================================================== *
 *  Editor base class                                                  *
 * ================================================================== */

/**
 * Shared ha-form based card editor. Subclasses provide the schema (and their
 * config defaults) — the identical value-changed → config-changed wiring,
 * ha-form creation/reuse and render loop live here (UI-NFR-015 §2.1, R-020).
 * No Shadow DOM (UI-NFR-015 R-022).
 */
export class KamerplanterCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...this._defaultConfig(), ...config };
    if (this._hass) this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  /** Per-card config defaults merged over the incoming config. */
  _defaultConfig() {
    return {};
  }

  /** Per-card ha-form schema. Rebuilt each render so entity pickers stay live. */
  _schema() {
    return [];
  }

  /** Whether the schema uses ``helper`` texts (wires computeHelper). */
  get _usesHelpers() {
    return false;
  }

  async _scheduleRender() {
    await haFormReady();
    this._render();
  }

  _render() {
    if (!this._config || !this._hass) return;

    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (e) => {
        this._config = e.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          }),
        );
      });
      this.appendChild(this._form);
    }

    this._form.hass = this._hass;
    this._form.schema = this._schema(this._hass);
    this._form.data = this._config;
    this._form.computeLabel = (schema) => schema.label || schema.name;
    if (this._usesHelpers) {
      this._form.computeHelper = (schema) => schema.helper || "";
    }
  }
}

/* ================================================================== *
 *  Device entity resolution                                           *
 * ================================================================== */

/** Known object-id suffixes, used only as a last-resort fallback. */
const KP_KNOWN_SUFFIXES = [
  "phase",
  "days_in_phase",
  "days_until_watering",
  "nutrient_plan",
  "active_channels",
  "phase_timeline",
  "next_phase",
  "status",
  "plant_count",
  "needs_attention",
];

/**
 * Collect the sensor states of a Kamerplanter device keyed by a stable suffix
 * (e.g. "phase", "days_in_phase", "nutrient_plan").
 *
 * Entity IDs are NOT guaranteed to carry a "kp_" prefix: with has_entity_name
 * HA derives them from the device name (e.g. "sensor.draca_0616_owl_growth_phase")
 * and the object-id suffix ("growth_phase") does not always equal the
 * translation key ("phase"). The entity's ``translation_key`` is therefore the
 * authoritative map key; unique_id parsing and a known-suffix match remain as
 * fallbacks for entities that predate translation keys.
 */
export function getEntityMap(hass, deviceId) {
  if (!deviceId || !hass) return {};

  const map = {};
  for (const ent of Object.values(hass.entities || {})) {
    if (ent.device_id !== deviceId) continue;
    if (!/^(?:sensor|binary_sensor)\./.test(ent.entity_id)) continue;
    const st = hass.states[ent.entity_id];
    if (!st) continue;

    // Preferred: translation_key (HA 2024.1+) — stable regardless of entity_id.
    if (ent.translation_key) {
      map[ent.translation_key] = st;
      continue;
    }

    // Fallback: unique_id always ends with _kp_{slug}_{suffix}.
    const kpParts = (ent.unique_id || "").split("_kp_");
    if (kpParts.length >= 2) {
      const rest = kpParts[kpParts.length - 1];
      const underIdx = rest.indexOf("_");
      if (underIdx > 0) {
        map[rest.substring(underIdx + 1)] = st;
        continue;
      }
    }

    // Last resort: match the object-id against known suffixes.
    const objId = ent.entity_id.replace(/^[^.]+\./, "");
    for (const s of KP_KNOWN_SUFFIXES) {
      if (objId.endsWith("_" + s)) {
        map[s] = st;
        break;
      }
    }
  }
  return map;
}

/** Resolve a device's display name (user override wins). */
export function getDeviceName(hass, deviceId) {
  if (!deviceId || !hass) return null;
  const dev = Object.values(hass.devices || {}).find((d) => d.id === deviceId);
  return dev ? dev.name_by_user || dev.name : null;
}

/* ================================================================== *
 *  i18n utility (Kataloge liefert WP-16)                              *
 * ================================================================== */

/**
 * Pick the card language ("de"/"en") from the HA context. Falls back to "en"
 * for any non-German locale so English HA users get English card texts.
 */
export function pickLang(hass) {
  const lang = hass?.language || hass?.locale?.language || "en";
  return String(lang).toLowerCase().startsWith("de") ? "de" : "en";
}

/**
 * Translate ``key`` against a ``{ de: {...}, en: {...} }`` catalog for the
 * current HA language. Missing keys fall back to the key itself. Optional
 * positional args substitute ``{0}``, ``{1}``, ... placeholders.
 */
export function t(catalog, key, hass, ...args) {
  const lang = pickLang(hass);
  const table = (catalog && (catalog[lang] || catalog.en || catalog.de)) || {};
  let str = table[key];
  if (str == null) str = key;
  if (args.length) {
    str = String(str).replace(/\{(\d+)\}/g, (m, i) => {
      const idx = Number(i);
      return idx < args.length ? String(args[idx]) : m;
    });
  }
  return str;
}
