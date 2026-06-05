# Audiences — Kamerplanter Home Assistant Integration

<!--
Produced following spec/project/audience-identification/. Audiences are derived
from the repository's README and purpose, not invented. Do not add audiences
without first declaring the bounded context.
-->

## Bounded context

A HACS-distributed Home Assistant custom integration that connects a self-
hosted Kamerplanter instance to Home Assistant, exposing plant monitoring,
nutrient dosages, tank management, and per-location overviews as sensors and
services.

**Inside the boundary**

- The custom integration under `custom_components/` (config flow, sensors, services)
- The HACS distribution metadata (`hacs.json`)

**Outside the boundary**

- Home Assistant Core (the host platform)
- The Kamerplanter backend (separate repo; consumed via its API)
- HACS distribution infrastructure

## Audiences

Each entry: label, relationship category, interaction surface, expectation,
documentation `track` (per spec/project/docs-audience-tracks/), status, criticality.

### Direct consumers

- **Home Assistant user running Kamerplanter** — _category_: direct-consumer ·
  _surface_: the HA UI, the integration's sensors and services, HACS install ·
  _expects_: reliable plant/nutrient data from Kamerplanter and dashboard-ready attributes ·
  _track_: `user-docs` · _status_: `assumed` · _criticality_: primary
- **Self-hoster running both Kamerplanter and Home Assistant** — _category_: operator ·
  _surface_: installing and configuring the integration against a Kamerplanter URL and token ·
  _expects_: a stable config flow and a documented setup path ·
  _track_: `developer-docs` · _status_: `assumed` · _criticality_: primary

### Contributors / maintainers

- **Maintainer (`nolte`)** — _category_: contributor ·
  _surface_: the integration source, CI, the specs under `spec/` ·
  _expects_: green CI and spec-grounded changes ·
  _track_: `developer-docs` · _status_: `assumed` · _criticality_: primary
- **Claude Code as co-author** — _category_: contributor ·
  _surface_: `CLAUDE.md`, `.claude/`, the Taskfile ·
  _expects_: deterministic task targets and readable conventions ·
  _track_: `developer-docs` · _status_: `assumed` · _criticality_: secondary

### Indirect audiences

- **Home Assistant Core and HACS** — _category_: indirect ·
  _surface_: the HA integration API/conventions and the HACS custom-repository manifest ·
  _expects_: (without knowing) a valid HACS manifest, semver releases, and HA-conformant integration code ·
  _track_: `developer-docs` · _status_: `assumed` · _criticality_: secondary

## Revisit triggers

Re-run `audience-identify revisit` when any of the following changes:

- The integration moves from HACS-custom to the HACS default store.
- The Kamerplanter API contract this integration consumes changes shape.
- A second smart-home platform is targeted.
