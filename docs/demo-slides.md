# Demo Slide Drafts

Copy/paste these into your slide tool. Two slides only &mdash; everything else
runs from terminal, browser, or editor (per `docs/demo-runbook.md`). Notes
below each slide are talking points, not the slide body.

---

## Slide 1 &mdash; Beat 1 (0:00&ndash;3:00)

**Title:** Find & Make Matchup &mdash; Harmony Service

**Subtitle:** Automating SeaBASS &times; satellite L2 matchup for OB.DAAC / PACE

**Body (3 bullets):**

- **Problem.** Validating ocean-color L2 products against in-situ SeaBASS
  measurements is done by hand, per-PI, per-reprocessing. Not reproducible,
  not at scale.
- **Solution.** A Harmony service that takes a paired
  (SeaBASS file, L2 granule) STAC item and returns an augmented SeaBASS
  file with per-record satellite matchup statistics. Same row count, same
  scientist's file format.
- **Status today.** Active prototype, public image auto-publishing to
  DockerHub, demo follows.

**Speaker notes:**
- "Today this is a manual notebook step per scientist. We're moving it
  into Harmony so any registered (SeaBASS file, L2 granule) pair becomes
  a one-call job."
- If asked about scope vs. existing tools: "this prototype focuses on the
  ingestion + matchup step. Downstream stats, plots, QA flags stay in the
  scientist's existing workflow &mdash; we hand them a SeaBASS file they
  already know how to work with."

---

## Slide 5 &mdash; Beat 5 (21:00&ndash;23:00)

**Title:** Pipeline Status

**Body (status checklist):**

| Stage | State |
| --- | --- |
| Local build (`make build-image`) & live invoke | &check; working, ~12 s per granule |
| CI: Python syntax check on every push | &check; green |
| CI: Docker image build + publish to DockerHub | &check; green on every push to `main` |
| DockerHub image `seadas/find-make-matchup-harmony` | &check; public, ~545 MB, tags `latest` + `sha-<commit>` |
| Reproducibility: pulled image output vs. reference fixture | &check; byte-identical (SHA256 match) |
| Harmony service-registry entry for `find-make-matchup-harmony` | &#x23F3; pending NASA / Earthdata side |
| Bamboo deploy to SIT &rarr; UAT &rarr; prod Harmony envs | &#x23F3; pending registry entry |

**Headline metric (for the slide footer or pull-quote):**

> Image rebuild + push to DockerHub on every commit. End-to-end
> reproducibility verified: pulled image produces SHA-identical output
> to the locally-built reference.

**Speaker notes:**
- "Every checkmark on this slide is a thing the demo just showed or could
  show on request. The two pending items are organizational, not
  technical."
- If asked when prod-Harmony goes live: "Image is ready. We need the
  Harmony service registry entry, which is an Earthdata-side ticket;
  once that lands, `bin/deploy-service` pushes our image tag to the
  Harmony env and we're done."
- If asked about ECR vs DockerHub: "We moved off ECR per ops guidance.
  Pipeline behavior is identical from the consumer's perspective; the
  registry URL is different."

---

## Convert-to-slide-tool cheatsheet

- **PowerPoint / Keynote.** Each `##` becomes a slide title. Each `###`
  becomes a sub-bullet section. Tables paste as tables.
- **Google Slides.** Use *Insert &rarr; Table* for the status grid, then
  paste cell-by-cell. The &check; / &#x23F3; characters render fine.
- **Markdown-native (reveal.js / Marp / Slidev).** This file is already
  shaped for those &mdash; the `---` separators are slide breaks.

## What lives on actual slides vs. on screen

| Beat | Slide? | What's on screen |
| --- | --- | --- |
| 1. Problem & motivation | **Slide 1** | Title + 3 bullets |
| 2. Architecture | no | GitHub preview of `docs/architecture.md` + open `transform.py` / `orchestrator.py` |
| 3. Harmony contract | no | Editor: `harmony/service-config.json`, `harmony/example-request.json`, `harmony/stac-item-shape.md` |
| 4. Live invoke | no (or fallback) | Terminal running `bin/demo-invoke`. If no docker on the laptop: editor open on `demo-backup/demo-invoke.txt`, scroll-and-narrate; see `demo-backup/README.md`. |
| 5. Pipeline status | **Slide 5** | Status checklist; switch to https://hub.docker.com/r/seadas/find-make-matchup-harmony for the "this is real" reveal |
| 6. Q&A | no | back to Slide 5 as a backdrop |
