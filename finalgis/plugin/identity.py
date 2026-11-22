"""FinalGIS product identity through supported Qt/PyQGIS extension interfaces.

Keep Qgs APIs, QGIS3 settings namespaces, project formats and provider IDs intact.
"""

from pathlib import Path

from qgis.core import Qgis, QgsProject, QgsSettings
from qgis.PyQt.QtCore import Qt, QTranslator, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

NAME = "FinalGIS"
VERSION = "0.3.0"
POSITIONING = "AI-Native Geographic Intelligence & World Creation"
ATTRIBUTION = (
    "Based on the open-source QGIS project. An independent Finalverse derivative."
)


class ProductTranslator(QTranslator):
    # Only exact product strings. Never translate copyrights, GIS terminology,
    # third-party plugins, paths, provider names or source/project content.
    STRINGS = {
        ("QgisApp", "Exit QGIS"): "Exit FinalGIS",
        (
            "QgisApp",
            "Do you really want to quit QGIS?",
        ): "Do you really want to quit FinalGIS?",
        ("QgsOptions", "QGIS Options"): "FinalGIS Settings",
        ("QgsOptionsBase", "QGIS Options"): "FinalGIS Settings",
        ("QgsPluginManager", "QGIS Plugin Manager"): "FinalGIS Plugin Manager",
    }

    STRINGS[("QgsOptions", "QGIS restart required")] = "FinalGIS restart required"
    for context in ("QgsOptions", "QgsOptionsBase"):
        for label in ("Style", "UI theme", "Font"):
            STRINGS[(context, label + " (QGIS restart required)")] = (
                label + " (FinalGIS restart required)"
            )
            STRINGS[(context, label + " <i>(QGIS restart required)</i>")] = (
                label + " <i>(FinalGIS restart required)</i>"
            )
        STRINGS[(context, "Check QGIS version at startup")] = (
            "Check QGIS foundation version at startup"
        )

    def translate(self, context, source, disambiguation=None, n=-1):
        return self.STRINGS.get((context, source))


class ProductIdentity:
    def __init__(self, workspace):
        self.workspace = workspace
        self.iface = workspace.iface
        self.window = self.iface.mainWindow()
        self.root = Path(__file__).parent
        self.translator = ProductTranslator(self.window)
        self.app = QApplication.instance()
        self.old_display = self.app.applicationDisplayName()
        self.dialogs = []
        self.actions = []

    def install(self):
        self.app.setApplicationDisplayName(NAME)
        self.app.installTranslator(self.translator)
        self.window.setWindowIcon(QIcon(str(self.root / "logo.png")))
        # The primary macOS About role belongs to FinalGIS. Original upstream
        # version, credits, sponsors, license and provider details stay reachable.
        self.original_help_actions = list(self.iface.helpMenu().actions())
        self.upstream_about = self.iface.actionAbout()
        self.old_about_text = self.upstream_about.text()
        self.old_about_role = self.upstream_about.menuRole()
        self.upstream_about.setMenuRole(QAction.MenuRole.NoRole)
        self.upstream_about.setText(
            "QGIS Foundation — Version, Contributors and License"
        )
        about = QAction("About FinalGIS", self.window)
        about.setMenuRole(QAction.MenuRole.AboutRole)
        about.triggered.connect(self.show_about)
        self.iface.helpMenu().insertAction(self.upstream_about, about)
        welcome = QAction("Welcome to FinalGIS", self.window)
        welcome.setMenuRole(QAction.MenuRole.NoRole)
        welcome.triggered.connect(self.show_welcome)
        self.iface.helpMenu().insertAction(self.upstream_about, welcome)
        self.foundation_menu = self.iface.helpMenu().addMenu("QGIS Foundation")
        for action in self.original_help_actions:
            self.iface.helpMenu().removeAction(action)
            self.foundation_menu.addAction(action)
        help_action = QAction("FinalGIS Help", self.window)
        help_action.setMenuRole(QAction.MenuRole.NoRole)
        help_action.triggered.connect(self.show_help)
        source_action = QAction("FinalGIS Project / Source", self.window)
        source_action.setMenuRole(QAction.MenuRole.NoRole)
        source_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/finalverse/gis"))
        )
        self.iface.helpMenu().insertAction(welcome, help_action)
        self.iface.helpMenu().insertAction(
            self.foundation_menu.menuAction(), source_action
        )
        self.actions = [
            about,
            welcome,
            help_action,
            source_action,
            self.foundation_menu.menuAction(),
        ]
        self.window.windowTitleChanged.connect(self.update_title)
        project = QgsProject.instance()
        project.isDirtyChanged.connect(self.update_title)
        project.fileNameChanged.connect(self.update_title)
        self.update_title()
        if not QgsSettings().value("finalgis/welcomeShown/v2", False, type=bool):
            self.show_welcome()
            QgsSettings().setValue("finalgis/welcomeShown/v2", True)

    def update_title(self, *args):
        project = QgsProject.instance()
        title = (
            project.title()
            or project.baseName()
            or ("Untitled" if project.isDirty() else "")
        )
        title = (title + (" *" if project.isDirty() else "") + " — ") if title else ""
        expected = title + NAME
        if self.window.windowTitle() != expected:
            self.window.setWindowTitle(expected)

    def _dialog(self, title):
        dialog = QDialog(self.window)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(620)
        layout = QVBoxLayout(dialog)
        header = QLabel('<h1 style="margin:0">FinalGIS</h1><p>' + POSITIONING + "</p>")
        header.setWordWrap(True)
        header.setStyleSheet(
            "background:#102b40;color:#f4f9ff;padding:20px;border-radius:8px;"
        )
        layout.addWidget(header)
        self.dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda: self.dialogs.remove(dialog) if dialog in self.dialogs else None
        )
        return dialog, layout

    def show_welcome(self):
        dialog, layout = self._dialog("Welcome to FinalGIS")
        body = QLabel(
            "Map, edit and analyze with mature GIS tools.\n"
            "Prepare geographic world exports in World Engineering.\n\n" + ATTRIBUTION
        )
        body.setWordWrap(True)
        layout.addWidget(body)
        row = QHBoxLayout()
        for text, callback in [
            ("Start mapping", lambda: self.workspace.mode_changed(0)),
            ("Open project…", lambda: self.iface.actionOpenProject().trigger()),
            (
                "World Engineering",
                lambda: (self.workspace.show(), self.workspace.mode_changed(1)),
            ),
        ]:
            button = QPushButton(text)
            button.clicked.connect(
                lambda checked=False, fn=callback: (dialog.close(), fn())
            )
            row.addWidget(button)
        layout.addLayout(row)
        dialog.show()

    def show_help(self):
        dialog, layout = self._dialog("FinalGIS Help")
        body = QLabel(
            "Professional GIS: edit, inspect, analyze and save QGIS-compatible projects.\n\n"
            "World Engineering: load the supplied source layers, prepare a bounded native processing plan, "
            "review it, then approve a local export. An export does not publish or change a living world.\n\n"
            "Finalverse Cloud, Map Server, SpatialDB and MutSea connections require separate configuration. "
            "QGIS documentation, contributors and licensing remain under Help → QGIS Foundation."
        )
        body.setWordWrap(True)
        layout.addWidget(body)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.close)
        layout.addWidget(close)
        dialog.show()

    def show_about(self):
        dialog, layout = self._dialog("About FinalGIS")
        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(
            "<p><b>FinalGIS " + VERSION + "</b></p><p>" + ATTRIBUTION + "</p>"
            "<p>QGIS foundation " + Qgis.QGIS_VERSION + " · GPL-2.0-or-later<br>"
            "Copyright © QGIS contributors. FinalGIS product layer © Finalverse.</p>"
            "<p>Supported here: GIS editing/analysis, verified Montréal source layers, "
            "reviewed native processing plans and local world export.</p>"
            "<p>Cloud, Map Server and MutSea services are not configured in this desktop build. "
            "No world publication is implied by an export.</p>"
            '<p><a href="https://github.com/finalverse/gis">FinalGIS source</a> · '
            '<a href="https://qgis.org">QGIS project</a> · '
            '<a href="https://qgis.org/license/">QGIS license</a></p>'
        )
        body.setMinimumHeight(270)
        layout.addWidget(body)
        upstream = QPushButton("QGIS foundation: full version, credits and license…")
        upstream.clicked.connect(self.upstream_about.trigger)
        layout.addWidget(upstream)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.close)
        layout.addWidget(close)
        dialog.show()

    def uninstall(self):
        for dialog in list(self.dialogs):
            dialog.close()
        for action in self.actions:
            self.iface.helpMenu().removeAction(action)
        for action in self.original_help_actions:
            self.foundation_menu.removeAction(action)
        for action in self.actions:
            action.deleteLater()
        self.window.windowTitleChanged.disconnect(self.update_title)
        project = QgsProject.instance()
        project.isDirtyChanged.disconnect(self.update_title)
        project.fileNameChanged.disconnect(self.update_title)
        for action in self.original_help_actions:
            self.foundation_menu.removeAction(action)
            self.iface.helpMenu().addAction(action)
        self.upstream_about.setText(self.old_about_text)
        self.upstream_about.setMenuRole(self.old_about_role)
        self.app.removeTranslator(self.translator)
        self.app.setApplicationDisplayName(self.old_display)
