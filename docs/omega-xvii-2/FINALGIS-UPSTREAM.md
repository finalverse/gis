# FinalGIS upstream reconciliation

## Verified upstream facts (2026-11-20)

| Field | Value | How verified |
|---|---|---|
| upstream_repository | https://github.com/qgis/QGIS.git | `git ls-remote` |
| upstream_branch | `master` at `2d509708c18` (CMake: 4.3.0, RELEASE_NAME "Master") | raw `CMakeLists.txt` on master |
| latest_verified_stable_release | **QGIS 4.2.3** | tag list + `release-4_2` CMake = 4.2.3 |
| latest_verified_release_tag | `final-4_2_3` → `b041a18904a4dc9fdada8ecb2c84385054ddfee1` | fetched tag object |
| current LTR | `final-3_44_15` → `44b4ef051784192d6e4829dc008bca120e4d2388` | fetched tag object |
| "QGIS 4.4.0" | **Not released.** No tag, no `release-4_4` branch, master is 4.3 dev | `ls-remote` tags/heads |
| finalgis_source_commit | `876335ab7ae` (product layer on master `e35c88781a9`) | git |
| finalgis_binary_version | packaged desktop = QGIS 3.44.15-Solothurn (Qt 5.15.19, Python 3.12) | `foundation.lock.json` |
| finalgis_downstream_patchset | 79 files / 3,910 insertions, **all additive**: `finalgis/`, `docs/finalgis/`, an 8-line README preface | `git diff --stat` vs base |

FinalGIS is not labelled "QGIS 4.4.0-based" anywhere.

## Downstream patch inventory

| Class | Paths |
|---|---|
| Branding | `finalgis/branding/`, `finalgis/plugin/identity.py`, `logo.*`, `scripts/render_branding.py`, `product/launcher.c` |
| Packaging | `scripts/package_app.py`, `platform/*`, `foundation.lock.json` |
| GIS functionality | `src/*.cpp` (native worker, C17 ABI), `typed-plan.schema.json`, `fixtures/montreal/` |
| Integration | `scripts/export_fwd.py`, `publish_reviewed.py`, `readback_scene.py`, `spatialdb_exchange.py`, `prepare_viewer.py`, `services/*` |
| Build compatibility | `finalgis/CMakeLists.txt` (standalone; does not touch the QGIS build) |
| Temporary workaround | none in QGIS sources; the "frozen Storm adapter" lives outside this repository |

No upstream QGIS C++ API is renamed and no upstream file is modified. That is why the reconciliation is mechanical.

## Reconciliation branch

`feat/finalgis-upstream-4.2.3-20261120` = `cf8790f5519`. Its parent is `final-4_2_3`, and it adds the identical product layer (an empty diff against `876335ab7ae` for `finalgis/` and `docs/finalgis/`) plus a README preface that names 4.2.3 as the source base. It applied without conflicts. The branch was composed with git plumbing (a temporary index), so no 1.2 GB checkout was needed.

The difference to the previous base: master `e35c88781a9` is 2,366 commits ahead of the 4.2 branch point; 4.2.3 carries 201 release-only commits.

## Runtime decision

The packaged desktop **stays on 3.44.15 LTR**:

- The official 4.2.3 macOS build crashes at startup on macOS 27.2 ([qgis/QGIS#67981](https://github.com/qgis/QGIS/issues/67981), still open on 2026-11-20). Ω-XVII.0 reproduced the crash before plugin load.
- The 4.2.3 headless providers pass, so the server/processing side can move first.

## Source build status (blocked, not claimed)

`git archive final-4_2_3` was configured server-only (`WITH_GUI=OFF WITH_DESKTOP=OFF WITH_SERVER=ON WITH_BINDINGS=OFF`, Qt 6). Dependency discovery, in order:

1. bison ≥ 3 and flex (system bison is 2.3). Installed with Homebrew (keg-only).
2. libzip. Installed.
3. libspatialindex ≥ 2.1 is refused by QGIS (libspatialindex#276), so `WITH_INTERNAL_SPATIALINDEX=ON` is used.
4. exiv2. Installed.
5. Qt6Keychain. Installing it upgraded Homebrew qtbase to 6.12 and broke the Qt module set; see HANDOFF-BASELINE.md. Configure now stops on the inconsistent Qt installation (`Qt6::harmonydeployqt` missing from the 6.12 qtbase vs the 6.11 meta-package).

To finish the source build, choose one route:

- Restore qtbase 6.11.1 and build qtkeychain from source into a private prefix, or
- move the whole Homebrew Qt set to 6.12 together.

Either needs the owner's approval because it changes shared system packages. Expected cost: about 6–10 GB of build tree and 1–2 hours on the M1. The working 3.44.15 candidate and all Ω-XVII.1 artifacts are untouched.

## Next steps

1. Fix the Qt environment (owner approval), then build `qgis_server` 4.2.3 headless. QGIS Server can then become a second backend behind the Map Server gateway (the gateway backend contract is CGI, which QGIS Server also speaks).
2. Re-run the FinalGIS plugin tests on a 4.2.x desktop once #67981 is fixed upstream.
