---
mission_statement: "kamerplanter-ha connects a Kamerplanter instance to Home Assistant as a HACS-distributed integration, so Home Assistant users and self-hosters see plant monitoring, nutrient dosages, tank state, and per-location overviews as Home Assistant sensors and services."
relevant_outcomes: [O-1, O-2]
audiences:
  - Home Assistant user running Kamerplanter
  - Self-hoster running both Kamerplanter and Home Assistant
verifies_via: F-1:acceptance-1
time_bound:
  kind: mvp_completion
mvp_status: achieved
created: 2026-07-02
revised_at: null
---

## Statement

`kamerplanter-ha` connects a Kamerplanter instance to Home Assistant as a
HACS-distributed integration, so Home Assistant users and self-hosters see plant
monitoring, nutrient dosages, tank state, and per-location overviews as Home
Assistant sensors and services.

- **Specific**: the statement names *what* (a HACS Home Assistant integration for
  Kamerplanter) and *for whom* (Home Assistant users and self-hosters, resolved
  in `audiences`).
- **Measurable**: `verifies_via: F-1:acceptance-1`. After a HACS install, the
  integration exposes Kamerplanter plant monitoring as Home Assistant sensors.
- **Achievable**: the minimum viable product is the shipped
  `kamerplanter-home-assistant-integration` capability. Roadmap item R-1 carries
  `mvp: true`, `detail: fine`, and `target_sprint: 1`.
- **Relevant**: `relevant_outcomes: [O-1, O-2]`. Each entry resolves to an outcome
  in `project/goals.md`.
- **Time-bound**: `time_bound: { kind: mvp_completion }`. The bound is the moment
  the shipped minimum viable product reaches achieved status.

## Audiences

- **Home Assistant user running Kamerplanter**: the minimum viable product
  delivers Kamerplanter plant monitoring, nutrient dosages, tank state, and
  per-location overviews as Home Assistant sensors and services, so the user
  automates and dashboards them in Home Assistant.
- **Self-hoster running both Kamerplanter and Home Assistant**: the minimum
  viable product delivers one HACS-distributed integration that connects the two
  self-hosted systems, so the self-hoster wires them together without custom
  glue code.

## Verification

Feature **F-1: Exposed Kamerplanter entities** verifies the mission through
acceptance criterion 1: *"After a HACS install and configuration, the integration
exposes a Kamerplanter instance's plant monitoring as Home Assistant sensors."*
This is the `verifies_sprint_value` criterion for sprint 0001 and holds against
the shipped integration, so the minimum viable product records as `achieved`.

## Source

- **Audience artefact**: `AUDIENCES.md` at the `kamerplanter-ha` repository root,
  consulted at its current develop tip. The two `audiences` entries are the Home
  Assistant user and the self-hoster.
- **Outcomes referenced**: O-1, O-2 from `project/goals.md`.
- **Authored by**: the `mission-define` cascade (issue nolte/claude-shared#262
  mission-authoring backfill), 2026-07-02. The cascade models the minimum viable
  product retroactively. The integration capability already carried `status:
  active` when the repository adopted the planning suite, so the roadmap records
  R-1 as `status: done` and opens `mvp_status` at `achieved`.
