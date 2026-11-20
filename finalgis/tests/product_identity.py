"""Qt product contract checks with the actual pinned QGIS runtime."""

import importlib.util
import json
import pathlib
import sys
import tempfile

from qgis.core import QgsApplication, QgsProject, QgsSettings
from qgis.PyQt.QtCore import QCoreApplication, QSettings
from qgis.PyQt.QtWidgets import QAction, QMainWindow, QMenu

root = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
with tempfile.TemporaryDirectory() as folder:
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, folder)
    QgsApplication.setPrefixPath(sys.argv[3], True)
    app = QgsApplication([], True)
    app.initQgis()
    QCoreApplication.setApplicationName("QGIS3")
    spec = importlib.util.spec_from_file_location(
        "finalgis_identity", root / "plugin/identity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Iface:
        def __init__(self):
            self.window = QMainWindow()
            self.menu = QMenu(self.window)
            self.about = QAction("About QGIS", self.window)
            self.about.setMenuRole(QAction.AboutRole)
            self.menu.addAction(self.about)

        def mainWindow(self):
            return self.window

        def actionAbout(self):
            return self.about

        def helpMenu(self):
            return self.menu

    class Workspace:
        def __init__(self):
            self.iface = Iface()
            self.calls = []

        def mode_changed(self, n):
            self.calls.append(n)

        def show(self):
            pass

    workspace = Workspace()
    QgsSettings().setValue("finalgis/welcomeShown/v2", True)
    identity = module.ProductIdentity(workspace)
    identity.install()
    assert workspace.iface.window.windowTitle() == "FinalGIS"
    project = QgsProject.instance()
    project.setTitle("QGIS field campaign")
    identity.update_title()
    assert workspace.iface.window.windowTitle().startswith(
        "QGIS field campaign"
    ) and workspace.iface.window.windowTitle().endswith("FinalGIS")
    project.setTitle("")
    project.setDirty(True)
    identity.update_title()
    assert workspace.iface.window.windowTitle() == "Untitled * — FinalGIS"
    assert (
        app.applicationName() == "QGIS3" and app.applicationDisplayName() == "FinalGIS"
    )
    assert (
        workspace.iface.about in identity.foundation_menu.actions()
        and workspace.iface.about.menuRole() == QAction.NoRole
    )
    assert identity.translator.translate("QgisApp", "Exit QGIS") == "Exit FinalGIS"
    assert identity.translator.translate("UnknownPlugin", "QGIS copyright") is None
    assert identity.translator.translate("QgisApp", "QGIS project file") is None
    assert (
        QCoreApplication.translate("UnknownPlugin", "Keep this GIS label")
        == "Keep this GIS label"
    )
    assert (
        QCoreApplication.translate(
            "QgsOptionsBase", "Style <i>(QGIS restart required)</i>"
        )
        == "Style <i>(FinalGIS restart required)</i>"
    )
    identity.show_about()
    assert identity.dialogs[-1].windowTitle() == "About FinalGIS"
    identity.uninstall()
    app.processEvents()
    assert (
        workspace.iface.about.text() == "About QGIS"
        and workspace.iface.about.menuRole() == QAction.AboutRole
    )
    result = {
        "status": "PASS",
        "checks": [
            "primary product title",
            "project-authored QGIS text preserved",
            "technical settings namespace unchanged",
            "original upstream About retained",
            "exact-context translator excludes attribution/API/file types",
            "About dialog available",
            "unload restores upstream action/role",
        ],
    }
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    project.clear()
    del identity, project, workspace
    app.exitQgis()
