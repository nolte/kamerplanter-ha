---
id: F-1
title: Exposed Kamerplanter entities
status: done
roadmap_item: R-1
sprint: 1
created: 2026-07-02
ended: 2026-07-02
verifies_sprint_value: acceptance-1
consistency_check:
  performed_at: 2026-07-02
  agent_version: manual-fallback (retroactive; feature-consistency-reviewer not run cross-repo)
  findings:
    - kind: clean
      target: project/features/
      resolution: proceed
      evidence: "project/features/ empty (first decomposition); no feature-to-feature overlap possible."
    - kind: prior-art
      target: the shipped Home Assistant integration
      resolution: proceed
      evidence: "The HACS integration already exposes Kamerplanter data as HA entities; F-1 documents the exposure contract, it does not build new integration logic."
---

## Description

F-1 is the mission-verifying feature for the shipped
`kamerplanter-home-assistant-integration` capability. The HACS-distributed
integration connects a Kamerplanter instance to Home Assistant. The contract
holds when, after a HACS install and configuration, the integration exposes the
instance's plant monitoring as Home Assistant sensors. This holds against the
shipped integration, so the retroactive reconciliation records this feature as
`done` (issue nolte/claude-shared#262).

## Acceptance criteria

- [x] **acceptance-1** After a HACS install and configuration, the integration
  exposes a Kamerplanter instance's plant monitoring as Home Assistant sensors.
  _(This is the sprint value verifier.)_
- [x] **acceptance-2** Per-channel nutrient dosages, tank management, and
  per-location overviews are exposed as sensors and services.
- [x] **acceptance-3** The integration installs through HACS and passes hassfest
  validation.

## Test hooks

- **acceptance-1**: configure the integration against a Kamerplanter instance and
  inspect the created sensors; passing.
- **acceptance-2**: inspect the dosage, tank, and overview entities; passing.
- **acceptance-3**: the hassfest and HACS validation CI; passing.

## Consistency notes

Retroactive documentation feature: the integration predates the planning suite.
This feature introduces no new implementation. It exists so the mission's
`verifies_via: F-1:acceptance-1` and sprint 1's `value_statement` resolve to a
real acceptance criterion.

## References

- `project/portfolio.yml` capability `kamerplanter-home-assistant-integration`
- `AUDIENCES.md` audience "Home Assistant user running Kamerplanter"
- `README.md` (the exposed entities and services)
