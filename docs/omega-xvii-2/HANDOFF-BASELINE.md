# Ω-XVII.2 handoff baseline

Recorded 2026-11-20 on QMBP13-3 (Apple M1, 16 GB, macOS 27.2.1) when Claude Code took over from Codex.

## Verified starting state

| Item | Verified value |
|---|---|
| FinalGIS worktree | `~/Finalverse/dev/worktrees/finalgis-ai-20261120`, branch `feat/finalgis-ai-workflows-20261120`, HEAD `876335ab7ae`, clean |
| Implementation commit | `c3e18debaba` (per `OMEGA-XVII-1-DELIVERY.json`) |
| Branding candidate | `feat/finalgis-product-identity-20261120` at `95e15b68ec7` (worktree `finalgis-branding-20261120`) |
| Private evidence | `~/Finalverse/dev/finalgis-ai-20261120/` (FinalGIS.app 0.3, worker, mapserv rel-8-6-6, scene, publication, logs) |
| Acceptance report | `docs/finalgis/ACCEPTANCE.md`. It claims a bounded slice only. Generalized tools, survey accuracy and production hardening are excluded. |
| Packaged desktop runtime | Official QGIS **3.44.15 LTR** prebuilt (tag `final-3_44_15`, `44b4ef05178`), installer sha256 in `finalgis/foundation.lock.json` |
| Source checkout base | QGIS `master` at `e35c88781a9` (4.3.0 development), **not** a release |
| MapServer used in Ω-XVII.1 | Unmodified upstream `rel-8-6-6` (`7515cccfe75`), built under private evidence |
| Disk | 27 GiB free at start; 19 GiB after this milestone's builds |

## Reproduced baseline

A fresh Release build of the native worker against the recorded prefixes (`/opt/homebrew`, `dev/gw2-20261111/db-env`) passed `ctest` **4/4** (`finalgis_workflows`, `finalgis_c17_abi`, `finalgis_workflow_v2`, `finalgis_spatialdb_bridge`). Logs: `dev/omega-xvii-2-20261120/baseline-*.log`.

## Discrepancies found

1. **QGIS 4.4.0 does not exist.** Upstream tags end at `final-4_2_3` (`b041a18904a`). `master` reports 4.3.0 "Master". No `release-4_4` branch exists. See FINALGIS-UPSTREAM.md.
2. **Source and runtime differ.** The repository base is 4.3.0-dev `master`, while the shipped desktop is the 3.44.15 LTR binary. The lock file states this correctly, but "FinalGIS source" was never one QGIS version.
3. **`buildings.geojson` carries EPSG:2950 coordinates while GeoJSON semantics imply WGS84.** OGR reports a WGS84 layer CRS. Every consumer must declare EPSG:2950 explicitly; the Map Server catalog does so per layer.
4. **The Viewer world's "episode" store is a derived copy.** Its region is the same Earth region (`8699ab0c…/b96ee246…`) at revision 2989. The original Earth store is at revision 2984. Both are used only as read-only copies.
5. **No authoritative geographic binding exists for the Montréal region.** The descriptor pins none. The Ω-XV registration is `presentation_only`, with `surveyed:false` and no epoch.

## Concurrent activity and isolation

- New branches: FinalGIS `feat/omega-xvii-2-mapserver-20261120` (from `876335ab7ae`) and `feat/finalgis-upstream-4.2.3-20261120`. MapServer fork `feat/finalverse-map-server-20261120`. MutSea `feat/omega-xvii-2-native-projection-20261120`.
- Region stores were copied into `dev/omega-xvii-2-20261120/fixtures/` before use. The original Earth store digest is recorded in `earth-montreal-source.sha256`.
- Nothing was pushed, merged or deployed.

## Environment incident

`brew install qtkeychain`, run while probing the QGIS 4.2.3 source build, upgraded Homebrew `qtbase` 6.11.1 → 6.12.0 while the other Qt modules stayed at 6.11.1. Private-API modules such as `qml` (qtdeclarative) now fail to load. The 6.11.1 keg is intact. Restoring it is waiting on the owner's approval: uninstall `qtkeychain`, uninstall only `qtbase` 6.12.0_2, then `brew link qtbase`. Until then, the FinalGIS worker builds against qtbase 6.12 and passes its tests, because it uses only QtCore/QtNetwork public API.
