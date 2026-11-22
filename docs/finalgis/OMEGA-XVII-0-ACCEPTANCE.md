# FinalGIS 0.2 product identity acceptance candidate

20 November 2026. Worktree `/Users/wenyan/Finalverse/dev/worktrees/finalgis-branding-20261120`, branch `feat/finalgis-product-identity-20261120`, baseline `c1ba0725d3d27c3b2458a9559d923669541026d5`. Implementation commit `561f5b347582389c59b7293d3210e454371f866a`. Local source commits and resulting artifact hashes are recorded in the external `FINALGIS-DELIVERY.json` receipt. No push, merge, upstream submission, public release or deployment was performed.

## Result

A separate FinalGIS.app now contains its desktop foundation, own native C17 bootstrap, product UI layer and demo assets. The primary app menu, window/project title, native About role, welcome, product Help, settings restart labels and app metadata identify FinalGIS. QGIS credits/license/API documentation remain explicitly accessible under QGIS Foundation. Runtime PNG brand assets avoid the legacy SVG decoder failure. Source APIs, modules, provider identifiers, project formats and upstream source history remain unchanged.

The implementation is a packaged pinned QGIS 3.44.15 foundation plus the FinalGIS product layer. It is not a rebuilt QGIS 4.3 development engine. The new C17 launcher and existing independent C++ worker were built here. The source engine's original bytes match before derivative signing; code instruction hashes remain identical after required local re-signing. No official upstream signature/endorsement is claimed for the modified product.

## Executed checks

| Check | Result |
| --- | --- |
| Native worker Release build/tests | Passed 3/3: workflow, C17 ABI, SpatialDB readback bridge |
| Native worker ASan/UBSan build/tests | Passed 3/3; no claim of instrumentation of the entire third-party Qt/QGIS desktop |
| Qt product identity contracts | Passed against actual bundled QGIS/PyQt: title, dirty state, authored project text preservation, settings namespace, retained upstream action, null translation fallback, About and unload restoration |
| Actual GIS integration | Passed 6 checks:45 roof /93 road OGR features, CRS numerical agreement, GEOS geometry/buffer, GDAL raster, project write/read, native Processing reprojection |
| macOS GUI | Observed FinalGIS native app menu, title, About, retained upstream credits/license, welcome and product Help; settings all show FinalGIS restart terminology |
| GUI mapping / project compatibility | Local Montréal layers rendered in EPSG:2950; own `.qgz` saved and reopened successfully in the final package |
| Native 3D | Opened and rendered the current map as a plane in QGIS's native 3D window; this does not validate detailed generated 3D buildings/terrain or Storm integration |
| Themes | Default light and Night Mapping inspected in actual desktop; product panel/text remain readable |
| Product source parity | Packaged product module and private profile copies match the isolated source |
| Profile isolation | Native bootstrap pins its new private profile; attempted `--profile default` is refused |
| Bundle signing | Local ad-hoc signature verified; no notarization/release claim |

Desktop images were observed through native computer control in this chat. Exported splash artwork is an actual Qt-rendered product asset, not a screenshot of a running app. Full-window PNG exports and transient splash capture were not obtained; do not substitute those assets for GUI evidence.

## Reproduction

Use the actual baseline input/runtime pins in `finalgis/foundation.lock.json`. Existing source wrappers and data fixtures remain in their prior paths. Example local commands:

```sh
cmake -S finalgis -B NEW_BUILD -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/opt/homebrew;/Users/wenyan/Finalverse/dev/gw2-20261111/db-env" -DFINALGIS_PROJ_DATA_DIR=/Users/wenyan/Finalverse/dev/gw2-20261111/db-env/share/proj
cmake --build NEW_BUILD --parallel 2
ctest --test-dir NEW_BUILD --output-on-failure
python3 finalgis/scripts/package_app.py --qgis PINNED_QGIS_APP --worker NEW_BUILD/finalgis-worker --source finalgis/fixtures/montreal --output NEW_OUTPUT/FinalGIS.app --profile NEW_PROFILE
```

Use `--parallel 2` (separate arguments). Packaging requires fresh output/profile destinations, macOS/APFS copy support, Xcode clang/signing tools and the pinned foundation's Python/Qt. The worker still uses this Mac's pinned Qt 6/GDAL dependencies; this is not a portable distribution. ASan uses a separate build directory with `FINALGIS_SANITIZERS=ON`.

For bundled Python integration tests, set PYTHONHOME to `APP/Contents/Frameworks`, PYTHONPATH to its `Resources/qgis/python` and `Resources/python3.11/site-packages`, PROJ_DATA to `Resources/qgis/proj`, and QT_QPA_PLATFORM=offscreen. Run `finalgis/tests/qgis_integration.py` and `finalgis/tests/product_identity.py` with the contained Python 3.12 executable. Product UI/plugin tests use a separate settings namespace; runtime desktop uses the new private profile. Keep all original/user projects intact.

## Failures and limits

Introduced/resolved: derivative bundle Info invalidated the old signature; local derivative signing fixed it. Empty-string translator fallback suppressed unrelated text; null fallback and Qt regression checks fixed it. Test-harness argument/import failures were corrected and are retained as failed iterations. Pre-existing/exposed: legacy SVG embedded-image decoding crashed the Qt 5 image handler; runtime now uses the existing PNG. Existing null-action/font-alias warnings remain in the pinned desktop logs, without blocking the executed workflows. The earlier failed launch watchdog affected only disposable test profiles.

Not verified: full QGIS 4.3 source-engine compilation; Windows/Linux or Intel desktop execution; installers/notarization; portable dependency packaging; arbitrary plugin/version/locale parity. Branding lives in the supported product module: explicitly disabling it restores foundation UI; it is not hard-coded into every QGIS engine dialog. Upstream news, third-party content and technical file/API names deliberately retain QGIS identity. No live Cloud/FMS/MutSea publication service was created by this milestone. Public promotion as a finished release must wait for those packaging/distribution gates and user acceptance.

## Preservation and cleanup

The original official QGIS app, upstream engine/source, existing accepted projects/worlds and other branches remain preserved. Only a new task-owned smoke project was saved. No existing project was rewritten. Scope is confined to `finalgis/` and `docs/finalgis/`; no Qgs or provider symbols were renamed. Existing shell-launcher 0.1 packages remain historical evidence; the new delivered app path is explicit in the receipt.

To make space, only disposable private Ω-XV compiler files were removed: selected Rust rlib/rmeta/object/dependency files and Viewer object/PCH/PCM caches. Cleanup logs record scope and reclaimed space. All seven delivered Ω-XV binary hashes were checked before and after, and sources, worlds, apps and evidence were retained. No worktree relied upon by existing accepted artifact paths was deleted.

Next recommended milestone: FinalGIS AI-Native Geographic World Creation, reusing these boundaries and existing reviewed native processing/publication contracts.
