# Geographic registration (Workstream H)

The Montréal registration (`dev/omega-xv-20261119/geographic-registration.json`,
schema `finalverse.geographic-registration/0.2`, revision 1) maps EPSG:2950 +
CGVD2013 to MutSea region-local metres through a pinned PROJ pipeline and geoid
grid. It is `validation.status = derived_model`, `surveyed = false`, and
`authorization.scope = presentation_only`.

Ω-XVII.3 consumes it through Core's `libworld_convergence` (`fv_wc_registration_open`,
`fv_wc_to_asset`), which **refuses** to open a document that claims survey
certification, a different anchor or offset, or a missing grid hash. The same code
path serves three consumers:

| Consumer | Use | Label shown |
|---|---|---|
| Viewer console | authoritative region position → displayed E,N,U for Storm placement | "Presentation-only registration · not surveyed", plus `derived_model · scope presentation_only · EPSG:2950 → region-local · rev 1` |
| Storm scene-update | `position` (displayed) and `source_position_region_m` (authoritative), both sent | renderer frame `presentation_only: true` |
| AI agent | resident position → EPSG:2950 for Map Server GEOS queries | answers say "presentation proximity (registration not surveyed)" |

The classification is displayed exactly as declared and never upgraded. Implemented
checks: schema, scope/world/region/revision, CRS/datum/units/axes, pipeline identity
hash, grid hash, explicit null epoch and source accuracy. Survey-grade alignment
still needs real control points and validation evidence. Neither is available,
so the status stays presentation-only. Coordinate-epoch support stays declared-null.
