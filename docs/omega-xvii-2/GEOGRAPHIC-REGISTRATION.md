# Geographic registration

## Contract (reused, not replaced)

There are two existing documents, and no third schema was added:

| Document | Owner | Status for Montréal |
|---|---|---|
| `mutsea.geographic-binding/v1` (Earth) / `mutsea.world-placement/v1` (other worlds), pinned in the region descriptor by `(binding_id, sha256)` and stored in the `bindings` table | **MutSea (authoritative)** | Earth region `8699ab0c…/b96ee246…` pins **none** |
| `finalverse.geographic-registration/0.2` (Ω-XV) | operator-reviewed presentation relationship | exists: `validation.status=derived_model`, `surveyed=false`, `coordinate_epoch=null`, `authorization.scope=presentation_only` |

The directive's `WorldSpatialRegistration` model is produced as a **view** mapped from these fields. `finalgis-worker registration-validate` returns it under `model`. That view is a projection only and is never stored as a second source of truth.

| WorldSpatialRegistration field | Source |
|---|---|
| world_id / region_id / registration_revision | `world`, `region`, `revision` |
| registration_id | sha256 of the exact document bytes |
| source_horizontal_crs / source_vertical_crs | `source.crs` (EPSG:2950), `source.vertical_datum` (CGVD2013(CGG2013a)) |
| coordinate_epoch | `validation.coordinate_epoch` (null: unresolved) |
| world_frame / local_origin / axis_conventions / units | `destination.frame`, `source.origin`, source/destination axes, `metre` |
| transform_pipeline | `pipeline` (id, projected→CSRS, CSRS→WGS84 Helmert, geoid formula, grid sha256) |
| validation_status / accuracy_metadata | `validation.*` |
| provenance / authorization | `provenance`, `authorization` |

## Dataset values verified

- Roofs EPSG:2950 (NAD83(CSRS) MTM 8). The GeoJSON wrapper wrongly implies WGS84, so the CRS is declared explicitly.
- Roads EPSG:4326. DTM EPSG:3979 with CGVD2013 heights (`sources.json`).
- Geoid grid: an 11×11 CGG2013a clip, sha256 `afa759d1…`, now also at `finalgis/fixtures/montreal/registration/geoid.tif` (OGL-Canada attribution in README).

## Validation (implemented: `spatial.validate_registration`)

`finalgis-worker registration-validate --registration R [--geoid G]` (C++, PROJ C API):

1. Checks the schema, units, axes, destination frame and declared CRS.
2. Checks that the geoid file's sha256 equals the pinned digest.
3. Recomputes from the projected origin: EPSG:2950 → EPSG:4617, then `vgridshift` (h = H + N), then the declared Helmert pipeline to WGS84. It compares the result with the stored anchor (1 mm tolerance), then round-trips back to the origin.
4. Classifies the document. `surveyed=true` is accepted only with an epoch, a source accuracy and `control_points`. A non-presentation scope requires a supported survey.

Result for the Ω-XV document: **`valid_presentation_only_registration`**.

- Recomputed geoid undulation: −30.385 m.
- Anchor reproduced to **3.7 µm** horizontally and **1 nm** vertically. The round trip closes to 3e-8 m.
- The test suite (`tests/registration.py`) confirms the refusals: an anchor shifted by about 8 mm, a 1 cm height change, a surveyed claim with no control points, an authoritative scope with no survey, and a wrong grid digest.

This proves numerical consistency of a declared relationship. It does **not** prove survey accuracy, and it is labelled that way.

## Authority

- MutSea owns registration. The Map Server only **reads** the MutSea pin (`/v1/worlds/{id}/registration` → `authoritative_binding`) and, separately, the presentation document (`presentation_registration`).
- The native projection verifies a pinned binding document against `sha256(document) == version` and its `binding_id`. A world placement is also checked against its domain-separated version and its region.
- Aetheria's Skyreach store has a real `mutsea.world-placement/v1` pin, which is decoded and verified.

## Remaining blocker

Surveyed registration for Montréal needs independent control points and a resolved coordinate epoch. None are available in the repositories or evidence, and none were invented. Placement remains **presentation-only**.
