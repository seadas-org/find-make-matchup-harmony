flow Diagram: Harmony Matchup Service

This document contains an initial Mermaid sequence diagram describing the
proposed Harmony-based “Find & Make Matchup” workflow.

The goal is to represent the high-level interactions between the user,
Harmony, search services, HOSS, and the matchup container.

```mermaid
sequenceDiagram
    participant U as User / Client
    participant H as Harmony API
    participant S as CMR / Harmony Search
    participant HO as HOSS Subsetter
    participant M as Matchup Container

    U->>H: Submit matchup request<br/>(primary, secondary, spatial/temporal window, options)
    H->>S: Search primary granules
    S-->>H: Primary granule list

    H->>S: Search secondary granules<br/>(constrained by time window)
    S-->>H: Secondary granule list

    H->>HO: Subset primary granules<br/>(space/time/variables)
    HO-->>H: Subsetted primary data

    H->>HO: Subset secondary granules<br/>(space/time/variables)
    HO-->>H: Subsetted secondary data

    H->>M: Run matchup container<br/>(subsetted primary + secondary)
    M-->>H: Final matchup product<br/>(CSV/NetCDF + logs)

    H-->>U: Return output links + STAC metadata

