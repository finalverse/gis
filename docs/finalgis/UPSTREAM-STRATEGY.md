# Upstream and maintenance strategy

Canonical product repository: `https://github.com/finalverse/gis.git`. Its primary local checkout is `~/Finalverse/FinalGIS` (filesystem lookup is case-insensitive here). Baseline main is `c1ba0725d3d27c3b2458a9559d923669541026d5`. No upstream remote was added or mutated by this work.

The preserved source originally came from QGIS development commit `e35c88781a9baff59081dafd2a92dad969d87a6b`; root CMake reports 4.3.0 Master. The selected executable foundation is official QGIS 3.44.15 LTR, source/tag `44b4ef051784192d6e4829dc008bca120e4d2388` / `final-3_44_15`. Installer lineage and version/dependency pins are in `finalgis/foundation.lock.json`. The prior4.2.3 desktop failure is historical evidence, not a newly tested version in this milestone.

Keep product patches in `finalgis/`: native worker, supported PyQGIS extension, branding, launcher, platform metadata and packaging. Never globally rename Qgs, libraries, Python APIs, Processing/provider identifiers or file formats. Retain original AGENTS.md, COPYING and upstream authorship. No AI-authored issues, comments, reviews or changes were submitted to QGIS upstream. Work here is the user's explicitly requested Finalverse product layer.

For upgrades, inspect a specific upstream release/tag in an isolated worktree/profile; compare source/dependency and license changes; rebuild the independent native worker; rerun real provider, raster/vector, CRS, GEOS, Processing, project roundtrip and product-identity tests; inspect menus, splash, welcome, About and 3D on each claimed platform; then update the runtime lock and evidence. Never point the product at an untested latest download.

Expected conflicts are Qt/PyQGIS compatibility wrappers, QAction roles, customization/settings keys, app layout and platform signing. The bounded translator must return a null fallback for unknown contexts, preserve attribution, and test actual Qt translation behavior. Qt 5 desktop and Qt 6 worker remain separate processes. Include binary dependency audit, corresponding source, license copies and proper signing/notarization in release work. A new foundation needs fresh instruction/asset integrity and user-data coexistence checks.

Use reviewable isolated commits and merge accepted product patches through Finalverse's own repository. Historical and other active worktrees remain preserved where accepted artifact paths depend on them. Publishing, merging and deployment require explicit authorization.
