# Vision

`kamerplanter-ha` is the nolte portfolio's Home Assistant surface for
Kamerplanter. It is a HACS-distributed Home Assistant custom integration that
connects a Kamerplanter instance to Home Assistant, exposing plant monitoring
(growth phases, days-in-phase, next-phase predictions, nutrient-plan
assignments), per-channel nutrient dosages, tank management, and per-location
overviews as sensors and services. It is decoupled from the core Kamerplanter
system so it can track Home Assistant and HACS conventions independently.

## Outcomes

- **O-1**: Home Assistant users running Kamerplanter see plant monitoring,
  nutrient dosages, tank state, and per-location overviews as Home Assistant
  sensors and services. _(audience: Home Assistant user running Kamerplanter)_
- **O-2**: self-hosters running both Kamerplanter and Home Assistant connect the
  two through one HACS-distributed integration. _(audience: Self-hoster running both Kamerplanter and Home Assistant)_
