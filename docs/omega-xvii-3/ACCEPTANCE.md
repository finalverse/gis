# Ω-XVII.3 acceptance

Status: **local engineering candidate**. Everything listed as met was executed on
the Mac on 2026-11-21. Nothing was pushed, merged, published or deployed.

| # | Requirement | Result | Evidence |
|---|---|---|---|
| P0 | Recover and verify the Ω-XVII.2 baseline, isolate work | **met** | HANDOFF-BASELINE.md |
| A | MutSea live replication through the commit pipeline, no lock bypass, no second writer, commit-coupled (WorldLine outbox) | **met** | MUTSEA-REPLICATION.md, `cargo test --workspace` all pass, `tests/live.rs` 6/6 |
| A.4 | Recovery 1–10 (snapshot, catch-up, live, disconnect, missed commits, resume, duplicates, cursor expiry, resync, server restart) | **met** | live.rs + live_replica.py scenarios |
| B | Native live projection; invariants; differential with exact mismatch counts | **met, 0 mismatches** | NATIVE-PROJECTION.md, ctest 3/3 (release + ASan/UBSan), live acceptance 5/5 (release + ASan/UBSan) |
| C | Canonical FVP subscription contract (domain 3 schema 1.1), negotiation, bounds, malformed rejection, no cross-world leakage | **met** | FVP-LIVE-STREAMING.md, refusal tests (401/404/426/400) |
| D | Read-only Map Server world adapter, spatially filtered views, stale never shown as current | **met** | MAPSERVER-INTEGRATION.md; regression **73/73** (`fvmap-live-integration.json`); live head/nearby; 503 world_not_current while the authority is down, 200 after |
| E | Actual Viewer connected: selection, scene, residents, live transforms, camera, loading, disconnect, reconnect, resync, registration label | **met** (selection through the rail, no 3D picking) | VIEWER-STORM-INTEGRATION.md, `shots/demo/*.png` |
| E+ | Owner request: modern AI-native Viewer UI/UX with before/after screenshots | **met** | `shots/before-viewer-xv.png` vs `shots/demo/` |
| E.4 | Visual quality | **partial**: framing, legibility and the console improved; renderer features unchanged (frozen Ω-XV renderer) | |
| F | AI: typed plan → policy → deterministic execution → Viewer; presentation-only caveat; adversarial refusal | **met** | AI-WORLD-INTERACTION.md, agent records |
| G | FinalGIS 4.x: Qt verified (6.12, no change needed); source build; crash investigation | **met for build + launch**: QGIS 4.2.3 builds against Qt 6.12 + qca 2.3.12, launches to the main window without the reported crash, qgis_process buffer 45/45; not yet packaged/branded/Python-enabled, so the 3.44.15 app stays | FINALGIS-4X-STATUS.md, `shots/qgis-4.2.3-launch.png` |
| H | Registration validation, classification preserved, invalid registration rejected | **met** for presentation-only; survey-grade not available (no control points) | GEOGRAPHIC-REGISTRATION.md |
| I | Reliability: fault injection (authority restart, Viewer disconnect, dropped connections, duplicates, gaps, corrupted frames, slow consumers, unsupported versions); sanitizers; fuzz | **met** (Map Server restart covered by the Ω-XVII.2 suite in the 73/73 rerun) | ASan/UBSan, libFuzzer 1.28 M execs / 0 findings, proptest |
| I.3 | Performance measured, not invented | **met** (GPU timers unavailable) | PERFORMANCE.md |
| 12 | Montréal Living World Acts 1–12 with Viewer screenshots | **met** | MONTRÉAL-LIVING-WORLD.md, `montreal-demo-evidence.json` |

## Open items

1. FinalGIS 4.2.3: Python bindings, branding layer and bundle, then a GIS compatibility suite before replacing the 3.44.15 app; capture a backtrace of the packaged #67981 crash for comparison.
2. Click-to-select in the 3D view (ray picking) and a zero-copy Storm surface (still the Ω-XV CPU frame bridge, ≈4 frames/s).
3. TLS for the replication transport and a production identity provider (local tokens today).
4. Core FVP registry entry for domain 3 schema 1.1 (`docs/native/FINALVERSE-FVP-SPECIFICATION.md` in Core).
5. Multi-region world subscriptions (one region per subscription today; the cursor is per region by design).

## Rollback

Every change is on a new local branch: mutsea `feat/omega-xvii-3-live-replication-20261121`,
MapServer `feat/omega-xvii-3-map-live-world-20261121`, FinalGIS
`feat/omega-xvii-3-living-agent-20261121`, viewer `feat/omega-xvii-3-living-viewer-20261121`.
The Ω-XVII.2 branches and binaries are unchanged. To roll back, stop using these
branches and evidence binaries. The only environment changes are `brew install gsl
qscintilla2` by Claude and `brew install qca` by the owner (reverse with `brew uninstall qca qscintilla2 gsl`).
