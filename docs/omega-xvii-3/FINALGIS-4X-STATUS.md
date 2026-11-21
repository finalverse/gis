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

The compile reached step 827/3877 and stopped because QGIS 4 always requires
**QCA** (`QtCrypto`). Two ways forward were put to the owner: build QCA 2.3.10 from
KDE source into a private prefix, or `brew install qca`, which also upgrades
gnupg/gnutls/nss and others. The local safety check blocked building downloaded
third-party source without the owner's go-ahead. **Status: blocked on that decision.**

**Runtime crash.** The packaged 4.2.3 startup crash (upstream qgis/QGIS#67981, open)
can't be reproduced from source until the build links. The working branded
FinalGIS.app stays on the 3.44.15 LTR runtime, untouched.
