# FinalGIS 4.x status (Workstream G)

**Qt.** No restore was needed. The owner upgraded every Homebrew Qt module to 6.12
(qtbase 6.12.0_2, qtdeclarative 6.12.0_1, qttools 6.12.0_1, …). The mixed
6.12/6.11 state reported in Ω-XVII.2 is gone: QtCore, QtQml, QtQuick, QtGui,
QtWidgets, QtSvg, QtPositioning and QtMultimedia frameworks all report 6.12,
`qmake -query QT_VERSION` = 6.12.0, and lrelease/lupdate resolve. The 6.11.1 kegs are
still installed but unlinked. They were left alone (no uninstall was needed).

**Source build (QGIS 4.2.3 + FinalGIS product layer, `qgis-4.2.3-src`).** Configured
with Ninja against Qt 6.12.0 (desktop + GUI, no Python bindings, no 3D/PDAL/GRASS):
`dev/omega-xvii-3-20261121/qgis-4.2.3-configure-*.log`. Fixes along the way, all
local and reversible: Homebrew `bison`/`flex` paths, `brew install gsl` (no deps),
`brew install qscintilla2` (depends only on qtbase; it also bumped fontconfig
2.18.3 → 2.18.4), internal spatialindex, explicit SQLite include, `WITH_PYTHON=OFF`.

The first compile stopped at 827/3877 because QGIS 4 always requires **QCA**
(`QtCrypto`). The owner ran `brew install qca` (qca 2.3.12, Qt 6 build) on
2026-11-21. After that, `WITH_AUTH=ON` found QCA and its OpenSSL plugin. The remaining
build fixes were all local to the build directory:

* OpenCL off (`USE_OPENCL=OFF`, the bundled cl2.hpp is missing), and EPT/COPC on with the
  bundled lazperf (4.2.3 compiles point-cloud sources even with them off).
* Protobuf consistency: the GIS environment's protoc 31.1 together with its headers and libraries,
  plus `CMAKE_PROJECT_INCLUDE=qgis-include-order.cmake`, which puts that environment's
  include directory first. This keeps Homebrew's protobuf 36 headers from shadowing
  the generated `vector_tile.pb.h`.

**Result: the build completes (2375/2375, 0 failures)**, logs
`dev/omega-xvii-3-20261121/qgis-4.2.3-build-5.log`. `qgis_process --version`: QGIS
4.2.3 'Belém do Pará', Qt 6.12.0. Compatibility check: `native:buffer` on the
Montréal buildings fixture wrote 45/45 features (same count as the input).

**Runtime crash.** The source-built desktop app was launched with a private
profiles directory (`qgis-run/profiles`, the owner's profiles were not touched). It
reached the full main window and the welcome/templates page and **did not crash**:
`shots/qgis-4.2.3-launch.png`, `qgis-run/run-1.log` shows only benign warnings, and
no new DiagnosticReports entry appeared. The crash reported for the packaged 4.2.3
(upstream qgis/QGIS#67981) is therefore **not reproduced** with a consistent Qt 6.12
source build on macOS 27.2. Of the candidate causes listed in the directive, that
points away from FinalGIS downstream changes (purely additive) and toward the
packaged runtime (bundled Qt ABI or packaging). This is an inference from one
successful launch, not a root-cause proof. A backtrace of the packaged crash was not
re-captured in this milestone.

**Not replaced.** The branded FinalGIS.app stays on the 3.44.15 LTR runtime. The
4.2.3 build has no Python bindings (`WITH_PYTHON=OFF`), so plugins and the
Processing Python providers are absent, and it is not packaged or branded yet.
Replacing the working app needs Python bindings, the branding layer, a bundle,
and a GIS compatibility suite.
