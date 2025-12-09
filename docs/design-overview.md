
---

## 3️⃣ `docs/design-overview.md`

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
- SeaDAS does not provide UI integration. It relies on local execution.
- The long-term goal is to provide a **Harmony-based workflow** that:
  - Uses CMR/Harmony search and HOSS subsetting
  - Runs matchup computation in a containerized environment
  - Produces standard matchup products (CSV/NetCDF) with STAC metadata

As this document evolves, it should capture both **current behavior** and the
**target Harmony implementation**.

---

## 2. Existing OB.DAAC Matchup Logic (Summary)

The current “Find and Make Matchup” capability at OB.DAAC is implemented through
the Python module `fd_matchup.py`. It performs pixel-level collocation between a
primary dataset and one or more secondary datasets (e.g., satellite-to-satellite
or satellite-to-in situ).

### 2.1 Inputs

Typical inputs include:

- Primary granule(s)  
- Secondary collection(s)  
- Time window (e.g., ±3 hours)  
- Spatial distance tolerance (pixel-to-pixel)  
- Pixel selection options  
- Optional geometry constraints (solar/viewing zenith, relative azimuth)  
- Quality filters (L2 flags, cloud masking)  
- Output format (CSV/ASCII)

### 2.2 Granule Discovery and Preparation

1. Parse metadata for the primary granule (time, footprint).  
2. Identify candidate secondary granules based on:
   - Time window  
   - Potential spatial overlap  

This may use CMR-like metadata queries or internal OB.DAAC indexing.

### 2.3 Temporal Filtering

For each secondary granule:
- Compute time difference with the primary
- Keep only granules within the user-specified Δt window

### 2.4 Spatial Filtering

For each remaining secondary granule:
- Load geolocation arrays  
- Perform coarse overlap filtering (bounding box or swath intersection)  
- Optionally refine with pixel-level distance checks  

### 2.5 Pixel-Level Matchup Computation

For each primary pixel:

- Find nearest valid pixel(s) in secondary dataset within distance tolerance  
- Compute:
  - Temporal difference  
  - Spatial separation  
  - Validity of angular constraints  

If all conditions pass, a matchup record is created.

### 2.6 Quality Screening

Apply quality masks such as:
- L2 flags  
- Cloud screening  
- Invalid or fill-value masking  

### 2.7 Output Generation

The tool writes a matchup product—typically CSV or ASCII—with fields such as:

- Coordinates of primary and secondary pixels  
- Δt (time difference)  
- Δd (distance)  
- Matched radiometric/reflectance values  
- Viewing geometry  
- Additional metadata needed for interpretation  

This output is consumed by downstream tools (e.g., SeaDAS).

---

## 3. Universal “Find Matchups” Service (SeaBASS Lead Request)

During discussions with the SeaBASS team, a clear and incremental path emerged for
implementing a Harmony-enabled matchup capability. The recommendation is to begin
with a **simple, universal, metadata-driven “Find Matchups” service**, before
progressing to more advanced or pixel-level “Make Matchups” workflows.

This section summarizes the SeaBASS lead’s request and describes how it aligns
with Harmony capabilities.

---

### 3.1 Objective

Develop a lightweight Harmony service that:

- Accepts a **list of target points** (geographic coordinates + timestamps)
- Searches specified **satellite collections** for temporally and spatially
  coincident granules
- Returns, for each target point, a structured list of matching granules

This service performs **metadata-only** matching (no file downloads, no pixel-
level extraction) and represents the simplest universal replacement for the
“find” component of existing OB.DAAC tools such as `fd_matchup.py`.

---

### 3.2 Inputs

The proposed inputs for the Universal Find Matchups service are:

1. **Target list**  
   A list of time–location pairs.  
   Each entry contains:
   - timestamp  
   - latitude  
   - longitude  

   Target lists may originate from:
   - SeaBASS (.sb) files  
   - Other file formats (CSV, Excel, netCDF, etc.)  
   - User-constructed lists  

2. **Time tolerance window**  
   A symmetric ±Δt defining the acceptable temporal separation between the target
   point and candidate granules.

3. **Collection(s) to query**  
   One or more OB.DAAC collections (e.g., PACE OCI L2, MODIS-Aqua L2, VIIRS L2).

4. *(Optional)* Additional filtering parameters  
   For future enhancement, the service may accept optional constraints such as:
   - platform/instrument selection  
   - day/night  
   - data type (e.g., L2 gen vs L2 bin)  
   - spatial tolerance overrides  

---

### 3.3 Outputs

For each target input point, the service returns:

- The list of **granules** from the specified collection(s) that fall within the
  temporal tolerance and whose spatial metadata (bounding box or swath polygon)
  suggests potential overlap.

The output includes collection and granule metadata such as:

- granule ID  
- collection ID  
- acquisition start/end time  
- spatial bounding box / polygon  
- (optional) URL for accessing granule metadata or download links  

This enables simple downstream usage, including:

- Selecting granules for download  
- Passing results to more complex “Make Matchup” workflows  
- Generating matchup candidate lists for SeaBASS, SeaDAS, or user-defined tools  

---

### 3.4 Implementation Notes (Harmony Perspective)

- The service can be implemented as a lightweight Harmony “Find-only” job:
  - Harmony forwards the target list and parameters to a container
  - The container performs CMR/Harmony Search queries
  - The container applies temporal and spatial filters
  - Results are returned in JSON/CSV

- No subsetting is required; therefore:
  - HOSS is not invoked
  - No L2 files are downloaded
  - No computation on geolocation arrays is needed

- This aligns well with Harmony’s strengths as a scalable search/aggregation
  orchestrator.

---

### 3.5 Relationship to Existing OB.DAAC Tools

This Universal Find Matchups service provides a cloud-native, API-accessible
alternative to the existing OB.DAAC scripts:

- **Replaces the “find” functionality** of `fd_matchup.py`
- Does **not** perform extraction (i.e., does not replace `mk_matchup.py` /
  `val_extract`)
- Enables users to build more complex workflows by supplying a clean set of
  matched granules

This also supports SeaBASS workflows by enabling automated creation of matchup
candidate lists from `.sb` files or other formats.

---

### 3.6 Path Forward

This universal “Find-only” capability provides a foundation for:

- Future enhancements to support more complex discovery logic
- Satellite-to-satellite matchup searches
- Eventually implementing a full **“Make Matchups”** Harmony service involving
  subsetting and pixel-level extraction

Starting with a simple and universal “Find Matchups” API is a strategically
sound and low-risk first step that supports multiple OB.DAAC use cases.


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

---

## 3.8 Limitations of Native CMR/Harmony Search Relative to Matchup Requirements

The existing CMR and Harmony Search capabilities are powerful for discovering
granules based on collection ID, temporal range, and coarse spatial metadata.
However, the full set of inputs and behaviors required for OB.DAAC matchup
workflows (Sections 2 and 3) extend beyond what CMR/Harmony search can natively
provide.

Key limitations that impact Find Matchups and Make Matchups workflows include:

### 3.8.1 Target-List Based Search
CMR does not support submitting an array of target points (time + latitude +
longitude) and receiving matches per target. Each target must be translated into
one or more individual search queries, and the aggregation of results must be
implemented by a higher-level service.

### 3.8.2 Per-Target Time Windows
While CMR supports temporal range filtering, it does not accept “per-target
±Δt” windows. For a list of targets, the service must compute individual
temporal windows and issue separate queries.

### 3.8.3 Spatial Distance Tolerances
CMR supports bounding box, polygon, and point searches, but it does not support:
- pixel-level distance tolerances (e.g., “within X km”), or
- target-specific spatial buffers  
These must be implemented in a downstream step (or approximated via metadata).

### 3.8.4 Geometry, Pixel Quality, and L2 Content-Based Filters
Key matchup inputs such as:
- viewing geometry constraints,
- solar/sensor zenith limits,
- L2 flags,
- cloud masking,
- radiance/reflectance validity,

are characteristics of the *data contents*, not the granule metadata. CMR does
not support filtering based on L2 variable contents or pixel-level attributes.
These must be handled by subsequent processing stages or custom containers.

### 3.8.5 Collection Relationships (Primary vs Secondary)
The concept of “primary vs secondary granules” is a logical construct of OB.DAAC
matchup tools, not a CMR search concept. Multiple coordinated searches and custom
logic are required to support this relationship.

---

### Summary

The Universal Find Matchups service must therefore:
- orchestrate multiple CMR/Harmony search calls,
- build per-target spatial and temporal queries,
- merge and organize results by target,
- apply additional logic beyond what CMR natively supports.

This confirms that the Find Matchups service will be a lightweight but necessary
intermediate layer between user-facing APIs and the underlying CMR/Harmony
search system.

## 4. Mapping to Harmony Components

See [`component-mapping.md`](component-mapping.md) for a detailed table.

At a high level:

- **Granule discovery** → Harmony / CMR search
- **Subsetting (space/time/variables)** → HOSS
- **Matchup computation** → New custom Harmony service/container
- **Output formatting** → Inside the container and/or via existing TRT services
- **STAC description** → Harmony job output

This section will be expanded once the mapping table is filled in.

---

## 5. Proposed Harmony Workflow (High-Level)

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

## 6. Inputs and Outputs

### 6.1. Expected Inputs

Examples:

- Primary collection ID (e.g., PACE OCI L2)
- Secondary collection ID(s)
- Time range or reference granule(s)
- Spatial constraints (region, track, point list)
- Matchup tolerances (time, distance, angle)
- Output format (CSV, NetCDF)
- Optional filters (quality flags, etc.)

### 6.2. Expected Outputs

- Matchup product file(s) (CSV or NetCDF)
- STAC metadata describing:
  - Inputs (collections, time range, region)
  - Processing steps (search, subset, matchup)
  - Provenance and parameters used

---

## 7. Diagrams

See [`workflow-diagram.md`](workflow-diagram.md) and the `diagrams/` directory
for Mermaid source and any exported PNGs/SVGs.


