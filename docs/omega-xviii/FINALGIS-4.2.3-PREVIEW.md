# FinalGIS 0.3.0 preview on QGIS 4.2.3 with Python (Ω-XVIII)

This continues `docs/omega-xvii-3/FINALGIS-4X-STATUS.md` as a separate workstream.
**FinalGIS.app is not replaced.** It stays on the 3.44.15 LTR runtime. The preview is a
separate bundle (`org.finalverse.finalgis.preview4`) with its own isolated profile.

## Python bindings

The QGIS 4.2.3 source build (Qt 6.12, Homebrew) was reconfigured with
`WITH_PYTHON=ON` and `WITH_BINDINGS=ON`. It uses Homebrew Python 3.15 and PyQt6 6.12.1
(Albert installed `pyqt`), plus a private venv that exposes sip 6.17 and PyQt-builder
to the build. Two problems surfaced:

1. **PyQt6 6.12 now ships its own `QMap<int, int>` mapped type.** QGIS 4.2.3 defines
   the same type, so sip-build refuses the core module ("the mapped type has already
   been defined in another module"). Downstream patch
   `finalgis/patches/qgis-4.2.3/0001-pyqt6-6.12-qmap-int-int.patch` guards the QGIS
   definition with `%If (- Qt_6_12_0)`. It is applied to the source tree used for this
   build, which is not a git checkout. With the patch, the full build finished with 0
   failures and `ninja install` succeeded.
2. **The install tree has no rpaths.** Executables and Python modules reference
   `@rpath/libqgis_*`, GDAL, PROJ and GEOS without any `LC_RPATH`. The build-tree
   binaries only worked because they carry build paths.

## Packaging (`finalgis/scripts/package_app_4x.py`)

- The script copies the installed bundle's `Contents`, renames the executable to
  `FinalGIS-engine`, and adds the branded launcher, icon, splash, notices, the native
  worker and the Montréal data.
- It adds `@loader_path`-relative rpaths, plus the two external library directories
  this local build links (gdal-env, Homebrew), to every Mach-O that uses `@rpath`: 40
  binaries. Each patched binary is re-signed ad hoc. Only load commands change: the
  engine's machine code is verified unchanged (`otool -tV`).
- `LSEnvironment` sets `PYTHONHOME` to Homebrew Python 3.15 (a QGIS mac bundle
  otherwise points Python at `Contents/Frameworks`). It also sets `PYTHONPATH` to the
  bundle's `qgis` package plus a private site directory, and `PATH` to the GDAL tools
  that match the linked GDAL 3.13.3.
- The private site directory holds `osgeo` (GDAL 3.13.3 bindings built for Python
  3.15 against the linked GDAL), `psycopg2`, and Processing's pure-Python dependencies
  (PyYAML, Jinja2, Pygments, OWSLib, requests, numpy, packaging). It sits outside the
  bundle.
- The pip metadata directory is moved out of `Contents/Frameworks`, because codesign
  treats it as a nested bundle.
- The isolated profile is `qgis.org/QGIS4.ini`. QGIS 4's application name is `QGIS4`;
  this was verified in the running app.
- The launcher (built with `-DFINALGIS_QGIS4`) writes the GUI customization as XML
  version 1, because QGIS 4 no longer reads the INI form.
- The result is ad-hoc signed and passes `codesign --verify --deep --strict`. It is
  not notarized and not portable, because it links Homebrew Qt and Python.

## Plugin under Qt 6

The FinalGIS plugin's `initGui` failed on PyQt5-style unscoped enums
(`QAction.NoRole`, and similar). It now uses scoped enums (`QAction.MenuRole.NoRole`,
`QDialogButtonBox.StandardButton.Close`, `QMessageBox.StandardButton.Yes`,
`Qt.WidgetAttribute.WA_DeleteOnClose`), which are valid in both PyQt5 and PyQt6.
`render_branding.py` was changed the same way.

## Compatibility (`finalgis/tests/compat_4x.py`): 11/11

The suite runs with the same environment the desktop app gets:

| Check | Result |
|---|---|
| `qgis_process --version` | QGIS 4.2.3 'Belém do Pará' |
| Providers | gdal, model, native, pdal, qgis, script (the Python providers load); 453 algorithms |
| `native:assignprojection` | declares EPSG:2950 on the Montréal buildings (the GeoJSON has MTM8 metres and no `crs` member) |
| `native:buffer`, `centroids`, `reprojectlayer`, `fixgeometries` | 45/45 features each; the WGS 84 output spans −73.558° to −73.548° and 45.504° to 45.511°, Old Montréal |
| `gdal:convertformat` (Python provider → ogr2ogr) | pass |
| PyQGIS layer + CRS + PROJ + GEOS | valid, 45 features, centre −73.5527, 45.5074; union GEOS-valid |
| FinalGIS plugin modules under QGIS 4 Python | import pass |

## Desktop launch

The preview was launched through LaunchServices (`open`). A probe script reported
the active plugins (`finalgis`, `processing`, `grassprovider`, `db_manager`,
`MetaSearch`) and the window title `FinalGIS` (`finalgis-4x/desktop-probe.json`). The
screenshots `shots/finalgis/finalgis-4.2.3-preview-desktop.png` and
`shots/finalgis/finalgis-4.2.3-preview-dialog.png` show the "Welcome to FinalGIS"
dialog. Earlier attempts, before each fix, are kept as
`launch-dialog.png` (missing `packaging`) and `dlg1.png` (the PyQt5 enum in
`initGui`).

## Not done

- The QGIS 4 start page (the news and templates panel) is upstream content and still
  says QGIS. The plugin brands the window, menus, dialogs and About.
- The splash: the XML customization is written, but the splash was not captured in
  this run.
- No portable bundle: Python, Qt and GDAL are linked from the system, not embedded.
- The preview does not replace FinalGIS.app. That needs an embedded runtime,
  notarization and a longer GIS regression run.
