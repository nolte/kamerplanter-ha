# Audiences — Kamerplanter Home Assistant Integration

<!--
Produced via the `audience-identify` skill, following
spec/project/audience-identification/ (sourced from the nolte-shared plugin).
Do not add audiences without first declaring the bounded context below.
-->

## Bounded context

- **What it is:** A HACS-compatible Home Assistant Custom Integration plus five
  vanilla-JS Lovelace cards that connect a Home Assistant instance to a running
  [Kamerplanter](https://github.com/nolte/kamerplanter) backend via REST API
  polling. Plant data, tank values, tasks, and calendar entries surface as
  native HA entities, services, and dashboard cards.
- **Boundaries:** the Python integration under `custom_components/kamerplanter/`,
  its bundled Lovelace cards under `www/`, its translations, and the bilingual
  end-user / developer documentation under `docs/de` and `docs/en`.
- **Explicitly outside:** the Kamerplanter backend itself (separate repository),
  Home Assistant Core, and HACS infrastructure.

## Audiences

Each entry: label, relationship category, interaction surface, expectation,
documentation `track`, open questions, `confirmed` or `assumed`, criticality.

### Direct consumers

- **Home Assistant end users (plant growers)** — _id_: `ha-end-users` · _category_: direct-consumer ·
  _surface_: HA UI, config flow, Lovelace cards, user guides (`docs/*/guides/`) ·
  _expects_: install via HACS, add the integration, see plants/tanks/tasks as
  entities, build dashboards and automations · _track_: `user-docs` ·
  _status_: `assumed` · _criticality_: primary
  - Open questions: none

### Operators

- **Self-hosting HA / Kamerplanter administrator** — _id_: `self-hosting-admin` · _category_: operator ·
  _surface_: config flow (backend URL, API key, tenant, Light mode), polling
  interval options, setup & troubleshooting guides · _expects_: connect HA to a
  reachable backend, manage auth and tenant selection, tune polling, diagnose
  connection failures · _track_: `user-docs` (override of the
  operator→developer-docs baseline: this integration's operator is the same
  self-hosting person as the end user and consumes the same guides) ·
  _status_: `assumed` · _criticality_: primary
  - Open questions: none (the "is the backend operator distinct?" question is
    resolved — see the dedicated Backend operator entry below).

- **Backend-only operator** — _category_: operator · _surface_: the REST API
  contract this integration consumes (endpoints, API-key auth, tenant model)
  plus the backend connection/config values surfaced in the config flow
  (backend URL, API key, tenant) · _expects_: a reachable Kamerplanter backend
  that exposes the endpoints, authentication, and tenant scheme this
  integration polls; awareness that this integration is a downstream consumer
  of backend API changes · _track_: `developer-docs` (portfolio baseline:
  a genuine operator who is not also the end user) · _status_: `assumed` ·
  _criticality_: secondary
  - Open questions: which concrete backend versions / API revisions this
    integration is validated against (currently untracked here).

### Contributors / maintainers

- **Maintainer (`nolte`) & integration / card developers** — _id_: `maintainers` · _category_: contributor ·
  _surface_: Python source, Lovelace card JS, tests, `Taskfile`, CI, the specs
  under `spec/`, development docs (`docs/*/development/`) · _expects_: local dev
  setup against a Kind cluster, architecture overview, test patterns, green CI,
  spec-grounded changes, deploy/verify cycle · _track_: `developer-docs` ·
  _status_: `assumed` · _criticality_: primary
  - Open questions: none

### Governing parties

- **HACS & Home Assistant Core quality gates** — _id_: `quality-gates` · _category_: governing-party ·
  _surface_: `manifest.json`, hassfest, HACS Action, brands repo, CI workflows ·
  _expects_: the integration meets HACS listing and HA quality requirements
  (manifest validity, brand assets, translations, SemVer releases) ·
  _track_: `developer-docs` · _status_: `assumed` · _criticality_: secondary
  - Open questions: none

### Indirect audiences

- **Kamerplanter backend maintainers** — _id_: `backend-maintainers` · _category_: indirect ·
  _surface_: the REST API contract this integration consumes · _expects_: that
  backend API changes are reflected here; this integration is a downstream API
  consumer · _track_: `developer-docs` · _status_: `assumed` ·
  _criticality_: peripheral
  - Open questions: none

## Open questions (cross-cutting)

- _Resolved (assumed):_ the Kamerplanter backend operator can be a distinct
  role from the Home Assistant operator. A dedicated "Backend-only operator"
  audience now captures this case under Operators above. Tagged `assumed` —
  not yet validated with a real representative.

## Revisit triggers

- A new public surface (e.g. an exposed config API, a webhook, MQTT discovery).
- A new deployment target beyond self-hosted HA (e.g. HA Cloud, add-on).
- The Kamerplanter backend introducing a multi-operator or hosted model.
- Promotion from HACS Custom to a HACS default / HA Core integration (new
  governing requirements).
