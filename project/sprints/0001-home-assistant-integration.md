---
number: 1
status: closed
started: 2026-07-02
ended: 2026-07-02
value_statement: A Home Assistant user installs the HACS integration and sees their Kamerplanter instance's plant monitoring, nutrient dosages, and tank state as Home Assistant sensors and services.
artifact_ref: develop (shipped capability, pre-planning-suite)
roadmap_items: [R-1]
features: [F-1]
---

## Goal

A Home Assistant user connects their Kamerplanter instance to Home Assistant
through the HACS-distributed integration and sees plant monitoring, nutrient
dosages, tank state, and per-location overviews as sensors and services. Success
is verified by F-1 `acceptance-1`: after a HACS install, the integration exposes
a Kamerplanter instance's plant monitoring as Home Assistant sensors.

## Features

- [F-1](../features/exposed-kamerplanter-entities.md): Exposed Kamerplanter entities, status: done

## Out of scope

- The core Kamerplanter system itself (a separate repository and API steward).
- Home Assistant Core and HACS themselves (upstream quality gates).

## Review notes

Retroactive reconciliation (2026-07-02): the
`kamerplanter-home-assistant-integration` capability already carried `status:
active` before this repository adopted the planning suite (issue
nolte/claude-shared#262 mission-authoring backfill). This sprint records roadmap
item R-1 and feature F-1 as `done`, and itself as `closed`, to document the
delivered minimum viable product rather than to plan new work.
