# Migration roadmap

## Done in Ω-XVII.2 (local, unpushed)

1. Finalverse Map Server gateway over unmodified MapServer (fork and rel-8-6-6 backends).
2. MutSea native read projection with native WorldLine verification and Rust differential (0 mismatches).
3. World Scene API with an FVP domain-3 event stream.
4. Registration validator and an honest presentation-only classification.
5. Typed AI spatial operations with a policy boundary.
6. A QGIS 4.2.3 product-layer branch.

## Next, in order

1. **Repair the Homebrew Qt environment** (owner approval), then build `qgis_server` 4.2.3 headless and add it as a second gateway backend.
2. **Live replication feed.** Subscribe the native layer to the Rust runtime's `Replication` sink or observer protocol. Keep the `(seq, hash)` cursor and domain-3 frames. Then serve live events through `/v1/worlds/{id}/stream` with long-poll or keep-alive.
3. **Register FVP domain 3 in Core** and add a Core-side golden-frame decoder test.
4. **Viewer data source** for the World Scene API, plus the WMS ground overlay. Requires foreground capture.
5. **Storm materials and lighting** for geographic scenes, coordinated with the Storm owners.
6. **Survey-grade registration**: obtain independent control points and a coordinate epoch for the Old Port area, then add `control_points` to a new registration revision. The validator already enforces the requirements.
7. **MutSea Next shadow replay** (TickRecord decoder, native kernel transitions per revision vs the Rust journal), then policy, then the writer-fence cutover design in MUTSEA-NEXT-ARCHITECTURE.md.
8. **Production hardening**: TLS front end, load and soak tests, OGC API Features/WFS exposure with tests, MapCache or WMTS for tiled delivery.
9. **Road topology** for `spatial.plan_route`. It stays unimplemented until a real network graph exists.

Pushes, merges, releases and deployments of any of the above need the owner's explicit approval.
