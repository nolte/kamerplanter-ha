# Roadmap

This file is the work queue governed by `spec/project/roadmap/`. Each entry is a
level-3 heading followed by a `yaml` code block (`id`, `title`, `detail`,
`outcomes`, `target_sprint`, `mvp`, `status`, in that order) and a free-text
body. `roadmap-plan` and `roadmap-refine` own the detail level and the status
lifecycle. Don't hand-edit those fields here.

Entries carry monotonically increasing IDs starting at `R-1`, never reused.
Outcome IDs (`O-n` in `goals.md`) are an independent counter.

`kamerplanter-ha` shipped the minimum-viable-product item below before adopting
the planning suite. This roadmap records it retroactively as `status: done`,
mapped to sprint 1, so the mission's minimum viable product resolves.

## Phase 1: Home Assistant integration

### R-1: HACS integration exposing Kamerplanter data

```yaml
id: R-1
title: HACS integration exposing Kamerplanter data
detail: fine
outcomes: [O-1, O-2]
target_sprint: 1
mvp: true
status: done
```

The HACS-distributed Home Assistant custom integration that connects a
Kamerplanter instance to Home Assistant and exposes plant monitoring, per-channel
nutrient dosages, tank management, and per-location overviews as sensors and
services. Capability `kamerplanter-home-assistant-integration` in
`project/portfolio.yml`.
