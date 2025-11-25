# Find & Make Matchup Harmony Service

This repository contains the analysis, design, and prototype development for a
**Harmony-based “Find & Make Matchup” service** that supports OB.DAAC and PACE
satellite data workflows.

The goal of this project is to translate the existing OB.DAAC matchup logic
(e.g., `fd_matchup.py`, SeaDAS integration) into a scalable Harmony workflow
using:

- Harmony / CMR search
- HOSS subsetting service
- A custom matchup computation container
- Optional CSV or NetCDF output services
- STAC-described outputs

---

## Repository Structure

```text
find-make-matchup-harmony/
│
├── docs/          # Design notes and documentation
├── diagrams/      # Sequence / architecture diagrams (source + exports)
├── prototype/     # Early prototype containers and code
├── harmony/       # Harmony job definitions and examples
└── README.md

