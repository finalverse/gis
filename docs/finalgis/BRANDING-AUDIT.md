# FinalGIS branding audit

20 November 2026. Baseline `c1ba0725d3d27c3b2458a9559d923669541026d5`, `finalverse/gis`, clean main checkout at `/Users/wenyan/Finalverse/FinalGIS`. Isolated branch `feat/finalgis-product-identity-20261120`. Existing Ω-XV exchange work remains on its separate branch; no unrelated source was overwritten.

The baseline had a branded shell launcher which executed a different official QGIS.app. Its bundle had FinalGIS metadata, while the actual host retained QGIS app menus, titles and About identity. The source checkout is QGIS development 4.3; the executed supported foundation is independently pinned QGIS 3.44.15 Solothurn / Qt 5.15.19 / Python 3.12. These are distinct from FinalGIS product version 0.2.0.

| Surface | Classification | Treatment |
| --- | --- | --- |
| Native bundle, Dock/application name, icon, Finder info | A: product | Separate full app bundle, FinalGIS name/identifier, existing Finalverse icon; C17 bootstrap launches its own contained engine |
| Main/project window title | A | FinalGIS; preserve project-authored names and dirty state, including text containing QGIS |
| Splash | A | New Qt-rendered product artwork, supported QGIS 3.44 customization path; transient startup splash not exported as a live screenshot |
| Welcome / primary About / Help | A | FinalGIS dialogs; product help and source entries precede explicit QGIS Foundation submenu |
| Settings restart labels | A | Exact-context replacements identify FinalGIS restart; no global substring rewriting |
| QGIS release checks | B/C: foundation | Explicit QGIS foundation version label; does not claim a FinalGIS updater |
| Qgs symbols, qgis Python modules, provider IDs, QGIS3 settings keys | B: technical | Unchanged |
| QGIS project format names and older-version compatibility warnings | B | Unchanged; .qgs/.qgz remain standard formats |
| Credits, license, donors, developer/API documentation | C: attribution | Original upstream dialog/actions retained under QGIS Foundation; GPL notice/source links and bundled license copy preserved |
| Upstream news, official plugin repository, third-party providers/plugins | D: external content | Correct upstream identities retained, never relabeled as Finalverse-owned services |

Implementation is contained in the existing `finalgis/` product extension/packaging layer plus this documentation. No QGIS engine C++ classes, namespaces or ABI symbols were renamed. The native engine signature must change for a derivative bundle; both architecture instruction sections match the original. Original official engine and app remain untouched. This is not a byte-identical signed official QGIS distribution.

Resolved failures: initial derivative Info.plist invalidated the old engine signature; local signing now accounts for it. The legacy embedded-image SVG crashed Qt 5's image handler; runtime icons now use the existing verified Finalverse PNG. An early translator returned an empty non-null string, suppressing fallback labels; it now returns a null translation and has a Qt fallback regression check. Crash-watchdog-disabled test profiles were reset only in this task's disposable namespace. An early diagnostic script omitted its `iface` import; the corrected probe is retained separately. These failures are not counted as passing checks.
