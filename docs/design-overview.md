
---

## 3️⃣ `docs/design-overview.md`

```markdown
# Design Overview: Find & Make Matchup Harmony Workflow

This document describes the **analysis and design** for a Harmony-based
"Find & Make Matchup" workflow for OB.DAAC, with an emphasis on PACE and
other ocean color missions.

It supports the initial design ticket to:

1. Understand the current OB.DAAC matchup logic  
2. Map existing components to Harmony services  
3. Propose an end-to-end Harmony workflow  
4. Define inputs, outputs, and data flow  
5. Provide diagrams and documentation for a future prototype implementation  

---

## 1. Background

- Existing OB.DAAC tools (e.g., `fd_matchup.py`) perform satellite-vs-satellite
  or satellite-vs-in-situ collocation.
- SeaDAS provides UI integration but relies on local execution.
- The long-term goal is to provide a **Harmony-based workflow** that:
  - Uses CMR/Harmony search and HOSS subsetting
  - Runs matchup computation in a containerized environment
  - Produces standard matchup products (CSV/NetCDF) with STAC metadata

As this document evolves, it should capture both **current behavior** and the
**target Harmony implementation**.

---

## 2. Existing OB.DAAC Matchup Logic (Summary)

> To be filled in as you review `fd_matchup.py` and related tools.

Suggested content:

- **Inputs**
  - Primary collection and granules
  - Secondary collection(s) and search parameters
  - Time and space tolerances
  - Angle / geometry constraints (if applicable)
  - Quality flags / filtering options

- **Processing steps**
  - How primary and secondary granules are discovered
  - How spatial and temporal matching is performed
  - Any interpolation or aggregation logic

- **Outputs**
  - File format (CSV, ASCII, NetCDF, etc.)
  - Variable/content structure (columns, groups, metadata)
  - How outputs are currently consumed (SeaDAS, downstream tools)

---

## 3. Mapping to Harmony Components

See [`component-mapping.md`](component-mapping.md) for a detailed table.

At a high level:

- **Granule discovery** → Harmony / CMR search
- **Subsetting (space/time/variables)** → HOSS
- **Matchup computation** → New custom Harmony service/container
- **Output formatting** → Inside the container and/or via existing TRT services
- **STAC description** → Harmony job output

This section will be expanded once the mapping table is filled in.

---

## 4. Proposed Harmony Workflow (High-Level)

High-level steps:

1. User submits a matchup request to Harmony with:
   - Primary collection and constraints
   - Secondary collection(s)
   - Spatial/temporal window
   - Matchup options and output preferences

2. Harmony:
   - Performs **Search** for primary granules
   - Performs **Search** for secondary granules within a time window
   - Uses **HOSS** to subset primary and secondary data
   - Sends subsetted data to a **Matchup container**

3. The matchup container:
   - Performs collocation / matching
   - Writes the final matchup product (e.g., CSV or NetCDF)
   - Optionally generates metadata for STAC

4. Harmony:
   - Registers the outputs as STAC items
   - Returns links to the user (download URLs + STAC metadata)

A more detailed sequence diagram is provided in `workflow-diagram.md`.

---

## 5. Inputs and Outputs

### 5.1. Expected Inputs

Examples:

- Primary collection ID (e.g., PACE OCI L2)
- Secondary collection ID(s)
- Time range or reference granule(s)
- Spatial constraints (region, track, point list)
- Matchup tolerances (time, distance, angle)
- Output format (CSV, NetCDF)
- Optional filters (quality flags, etc.)

### 5.2. Expected Outputs

- Matchup product file(s) (CSV or NetCDF)
- STAC metadata describing:
  - Inputs (collections, time range, region)
  - Processing steps (search, subset, matchup)
  - Provenance and parameters used

---

## 6. Diagrams

See [`workflow-diagram.md`](workflow-diagram.md) and the `diagrams/` directory
for Mermaid source and any exported PNGs/SVGs.

---

### 3.7 Optional Future Enhancement: Target List Generator

The SeaBASS team identified an important related use case that is adjacent to the
Universal Find Matchups service: the automated creation of **target lists** from
user-provided files. A target list is a standardized set of (timestamp,
latitude, longitude) pairs that serve as input to the Find Matchups service.

Currently, OB.DAAC users often derive these target lists from metadata contained
in SeaBASS (.sb) files, but other users may want to generate matchup targets
from CSV, Excel, or netCDF files. To support these use cases, a future optional
enhancement could be a **Target List Generator** that:

- Accepts one or more input files:
  - SeaBASS `.sb` files  
  - CSV/Excel tables  
  - netCDF datasets  
  - Other formats as needed  

- Extracts the relevant metadata fields:
  - Timestamp  
  - Latitude  
  - Longitude  

- Produces a standardized target-list structure suitable for the Universal Find
  Matchups API.

This proposed functionality is **deliberately separate** from the core Find
Matchups service. The Universal Find Matchups service should remain simple and
collection-agnostic, requiring the target list as input rather than generating
it. The Target List Generator should be considered a **future standalone
preprocessing tool**, which could be implemented either:

- as a dedicated Harmony service,  
- as a client-side utility,  
- or as a modular component feeding the Find Matchups workflow.

Separating this preprocessing step from the core Find Matchups capability keeps
the initial implementation simple and universal while still acknowledging the
long-term value of automated target-list creation for SeaBASS and other
data-driven workflows.

## 8. Next Steps

- Complete description of the current OB.DAAC matchup logic
- Fill in the component mapping table
- Refine the Harmony workflow and inputs/outputs
- Use this document as the basis for the first prototype container design

