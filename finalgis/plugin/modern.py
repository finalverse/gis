"""FinalGIS Modern (Ω-XIX): an optional, reversible workspace profile over the full QGIS desktop.

Nothing is removed: "Professional" restores every toolbar and panel exactly as it was. Modern
mode keeps the map first, puts the project browser and layers on the left, offers contextual
tools for the current layer, a searchable command palette (the QGIS locator, Ctrl+K, with a
FinalGIS filter: prefix "fg"), a FinalGIS home page in place of the upstream start page, and an
AI GIS assistant whose output is always labelled as a proposal until QGIS itself has computed
or the user has approved it. Destructive operations and publication require explicit approval.
"""
import json, os, pathlib, threading, urllib.request

from qgis.core import (Qgis, QgsApplication, QgsLocatorFilter, QgsLocatorResult, QgsMapLayerType, QgsProject,
                       QgsSettings, QgsWkbTypes)
from qgis.PyQt.QtCore import QObject, Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QAction, QIcon, QKeySequence
from qgis.PyQt.QtWidgets import (QDockWidget, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                                 QMessageBox, QPlainTextEdit, QPushButton, QToolBar, QVBoxLayout, QWidget)

ACCENT = "#6aa3ff"
STYLE = """
QWidget#fgHome { background: #0d121a; }
QWidget#fgHome QLabel { color: #dfe7f3; }
QWidget#fgHome QListWidget { background: #111722; color: #c9d3e1; border: 1px solid #1f2a3a; border-radius: 8px; }
QFrame#fgCard { background: #111722; border: 1px solid #1f2a3a; border-radius: 10px; }
QLabel#fgTitle { font-size: 20px; font-weight: 600; color: #eef3fb; }
QLabel#fgSub { color: #9aa6b8; }
QLabel#fgTag { color: #0b0f16; background: %s; border-radius: 6px; padding: 2px 8px; font-weight: 600; }
QPushButton#fgPrimary { background: %s; color: #0b0f16; border-radius: 8px; padding: 6px 12px; font-weight: 600; }
QPushButton#fgGhost { background: #182131; color: #dfe7f3; border-radius: 8px; padding: 6px 12px; }
QLabel#fgAi { color: #c9b6ff; }
QLabel#fgVerified { color: #63d6a0; }
""" % (ACCENT, ACCENT)

KEEP_TOOLBARS = {"mFileToolBar", "mMapNavToolBar", "mAttributesToolBar"}


class FinalGISLocatorFilter(QgsLocatorFilter):
    """Searchable FinalGIS commands inside the QGIS locator (Ctrl+K, prefix 'fg')."""

    def __init__(self, modern, commands=None):
        super().__init__()
        self.modern = modern
        self.commands = commands or modern.commands

    def clone(self):
        return FinalGISLocatorFilter(self.modern, self.commands)

    def name(self):
        return "finalgis"

    def displayName(self):
        return "FinalGIS commands"

    def prefix(self):
        return "fg"

    def fetchResults(self, string, context, feedback):
        q = (string or "").lower()
        for i, (label, desc, _fn, _destructive) in enumerate(self.commands()):
            if not q or q in label.lower() or q in desc.lower():
                r = QgsLocatorResult(self, label, i)
                r.description = desc
                self.resultFetched.emit(r)

    def triggerResult(self, result):
        label, _desc, fn, destructive = self.commands()[result.userData()]
        if destructive and QMessageBox.question(self.modern.window, "FinalGIS", f"'{label}' changes data or publishes. Continue?") != QMessageBox.StandardButton.Yes:
            return
        fn()


class _Worker(QObject):
    done = pyqtSignal(str, str)  # (kind, text)


class ModernWorkspace:
    def __init__(self, workspace):
        self.ws = workspace
        self.iface = workspace.iface
        self.window = self.iface.mainWindow()
        self.saved = {}
        self.active = False
        self.filter = None
        self.home = None
        self.assistant = None
        self.context = None
        self.worker = _Worker()
        self.worker.done.connect(self._assistant_result)

    # ------------------------------------------------------------------ commands
    def commands(self):
        ws = self.ws
        return [
            ("FinalGIS Modern workspace", "Map-first workspace with contextual tools (reversible)", lambda: self.set_active(True), False),
            ("Professional workspace", "Restore every QGIS toolbar and panel", lambda: self.set_active(False), False),
            ("Load verified Montréal layers", "Public sources, bounded study area", ws.load_layers, False),
            ("Prepare processing plan (AI)", "Typed plan proposal; nothing runs until you approve", ws.make_plan, False),
            ("Publish reviewed scene to SpatialDB", "Requires approval and the operator publication adapter", ws.publish_scene, True),
            ("Inspect layer CRS", "List every layer's CRS against the project CRS", lambda: self.ask("Inspect the CRS of my layers"), False),
            ("Discover datasets", "Summarise the layers in this project", lambda: self.ask("What data is in this project?"), False),
            ("Validate geometry of the current layer", "QGIS processing native:checkvalidity (read-only)", lambda: self.ask("Validate the current layer"), False),
            ("Open AI GIS assistant", "Ask about the data; proposals stay labelled", self.show_assistant, False),
            ("FINALVERSE scene preview", "Open the published hall in the FINALVERSE Viewer", self.preview_in_finalverse, False),
            ("About FinalGIS", "Product identity and QGIS attribution", ws.show_about, False),
        ]

    # ------------------------------------------------------------------ install
    def install(self):
        self.filter = FinalGISLocatorFilter(self)
        self.iface.registerLocatorFilter(self.filter)
        self.act_modern = QAction("FinalGIS Modern workspace", self.window)
        self.act_modern.setCheckable(True)
        self.act_modern.setShortcut(QKeySequence("Ctrl+Alt+M"))
        self.act_modern.toggled.connect(self.set_active)
        self.iface.addPluginToMenu("FinalGIS", self.act_modern)
        self.act_assistant = QAction("AI GIS Assistant", self.window)
        self.act_assistant.setShortcut(QKeySequence("Ctrl+Alt+A"))
        self.act_assistant.triggered.connect(self.show_assistant)
        self.iface.addPluginToMenu("FinalGIS", self.act_assistant)
        self._build_home()
        self._build_assistant()
        self._build_context()
        self.iface.currentLayerChanged.connect(self._refresh_context)
        if QgsSettings().value("finalgis/modern/active", True, type=bool):
            # After QGIS has restored its own window state (which would re-show every toolbar).
            self.iface.initializationCompleted.connect(lambda: QTimer.singleShot(300, lambda: self.act_modern.setChecked(True)))
        if os.environ.get("FINALGIS_DEMO_SCRIPT"):
            self.iface.initializationCompleted.connect(lambda: self.run_demo_script(os.environ["FINALGIS_DEMO_SCRIPT"]))

    def run_demo_script(self, path):
        """Reproducible evidence (development): a timed list of '<seconds> <action> [arg]' lines,
        executed through the same methods as the buttons; each 'mark NAME' is logged so an
        external capture can screenshot the real window."""
        log = pathlib.Path(os.environ.get("FINALGIS_LOG_DIR", "/tmp")) / "finalgis-demo-marks.log"
        steps = []
        for line in pathlib.Path(path).read_text().splitlines():
            if line.strip():
                t, rest = line.split(" ", 1)
                steps.append((float(t), rest))

        def do(rest):
            cmd, _, arg = rest.partition(" ")
            if cmd == "load":
                self.ws.load_layers()
            elif cmd == "ask":
                self.ask(arg)
            elif cmd == "select":
                for l in QgsProject.instance().mapLayers().values():
                    if arg.lower() in l.name().lower():
                        self.iface.setActiveLayer(l)
                        break
            elif cmd == "modern":
                self.set_active(arg != "off")
            elif cmd == "apply":
                if self.pending:
                    layer, field = self.pending
                    from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsStyle, QgsSymbol
                    idx = layer.fields().indexOf(field)
                    cats = [QgsRendererCategory(v, QgsSymbol.defaultSymbol(layer.geometryType()), str(v)) for v in sorted(layer.uniqueValues(idx), key=str)[:24]]
                    r = QgsCategorizedSymbolRenderer(field, cats)
                    r.updateColorRamp(QgsStyle.defaultStyle().colorRamp("Spectral"))
                    layer.setRenderer(r)
                    layer.triggerRepaint()
                    self.output.appendPlainText(f"APPLIED (scripted approval) · categorized style on '{layer.name()}'.")
            with open(log, "a") as f:
                f.write(f"{rest}\n")

        for t, rest in steps:
            QTimer.singleShot(int(t * 1000), lambda rest=rest: do(rest))

    def unload(self):
        self.set_active(False)
        if self.filter:
            self.iface.deregisterLocatorFilter(self.filter)
        for d in (self.home, self.assistant):
            if d:
                self.iface.removeDockWidget(d)
        if self.context:
            self.window.removeToolBar(self.context)

    # ------------------------------------------------------------------ modern / professional
    def set_active(self, on):
        if on == self.active:
            return
        self.active = on
        QgsSettings().setValue("finalgis/modern/active", on)
        if self.act_modern.isChecked() != on:
            self.act_modern.setChecked(on)
        if on:
            self.saved = {tb.objectName(): tb.isVisible() for tb in self.window.findChildren(QToolBar)}
            self.saved_docks = {d.objectName(): d.isVisible() for d in self.window.findChildren(QDockWidget)}
            for tb in self.window.findChildren(QToolBar):
                if tb.objectName() not in KEEP_TOOLBARS and tb is not self.context:
                    tb.setVisible(False)
            for d in self.window.findChildren(QDockWidget):
                name = d.objectName()
                if name in ("Browser", "Layers"):
                    self.window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, d)
                    d.setVisible(True)
            self.context.setVisible(True)
            self.home.setVisible(True)
            self.home.raise_()
            self._show_canvas_instead_of_upstream_start_page()
            self.iface.messageBar().clearWidgets()
            left = [d for d in self.window.findChildren(QDockWidget) if d.objectName() in ("Browser", "Layers")]
            if left:
                self.window.resizeDocks(left, [280] * len(left), Qt.Orientation.Horizontal)
            self.window.resizeDocks([self.home], [380], Qt.Orientation.Horizontal)
            if self.window.width() < 1200:
                self.window.resize(1400, 860)
            self.iface.messageBar().pushMessage("FinalGIS Modern", "Map-first workspace. Ctrl+K: command palette (prefix fg) · Ctrl+Alt+M: Professional.", Qgis.MessageLevel.Info, 6)
        else:
            for tb in self.window.findChildren(QToolBar):
                if tb.objectName() in self.saved:
                    tb.setVisible(self.saved[tb.objectName()])
            for d in self.window.findChildren(QDockWidget):
                if d.objectName() in getattr(self, "saved_docks", {}):
                    d.setVisible(self.saved_docks[d.objectName()])
            if self.context:
                self.context.setVisible(False)
            if getattr(self, "_stack", None) is not None:
                self._stack.setCurrentIndex(self._stack_prev)
            for w in getattr(self, "_hidden_welcome", []):
                w.setVisible(True)

    def _show_canvas_instead_of_upstream_start_page(self):
        """Modern mode shows the FinalGIS home panel instead of the upstream start page: the
        central stack switches to the map canvas (the upstream page is unchanged and returns in
        Professional mode)."""
        from qgis.PyQt.QtWidgets import QStackedWidget
        self._hidden_welcome = [w for w in self.window.findChildren(QWidget) if "Welcome" in w.metaObject().className() and w.isVisible()]
        for w in self._hidden_welcome:
            w.setVisible(False)
        canvas = self.iface.mapCanvas()
        for stack in self.window.findChildren(QStackedWidget):
            kinds = [stack.widget(i).metaObject().className() for i in range(stack.count())]
            if any("Welcome" in k for k in kinds):
                for i in range(stack.count()):
                    w = stack.widget(i)
                    if w is canvas or w.isAncestorOf(canvas):
                        self._stack, self._stack_prev = stack, stack.currentIndex()
                        stack.setCurrentIndex(i)
                        return True
        return False

    # ------------------------------------------------------------------ home (replaces the upstream start page in Modern mode)
    def _card(self, title, body, buttons):
        f = QFrame()
        f.setObjectName("fgCard")
        lay = QVBoxLayout(f)
        t = QLabel(title)
        t.setStyleSheet("font-weight:600;color:#eef3fb;font-size:14px;")
        lay.addWidget(t)
        b = QLabel(body)
        b.setObjectName("fgSub")
        b.setWordWrap(True)
        lay.addWidget(b)
        row = QHBoxLayout()
        for i, (label, fn) in enumerate(buttons):
            p = QPushButton(label)
            p.setObjectName("fgPrimary" if i == 0 else "fgGhost")
            p.clicked.connect(fn)
            row.addWidget(p)
        row.addStretch(1)
        lay.addLayout(row)
        return f

    def _build_home(self):
        self.home = QDockWidget("FinalGIS", self.window)
        self.home.setObjectName("FinalGISModernHome")
        w = QWidget()
        w.setObjectName("fgHome")
        w.setStyleSheet(STYLE)  # local: QGIS re-applies its own application stylesheet after start-up
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QIcon(str(self.ws.root / "logo.png")).pixmap(44, 44))
        head.addWidget(logo)
        col = QVBoxLayout()
        title = QLabel("FinalGIS")
        title.setObjectName("fgTitle")
        sub = QLabel("Geographic intelligence for FINALVERSE")
        sub.setObjectName("fgSub")
        col.addWidget(title)
        col.addWidget(sub)
        head.addLayout(col)
        head.addStretch(1)
        tag = QLabel("0.3 preview")
        tag.setObjectName("fgTag")
        tag.setFixedHeight(22)
        head.addWidget(tag, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(head)
        lay.addWidget(self._card("Start with Montréal", "Public roof outlines, road centrelines and NRCan elevation for a bounded 260 m study area.",
                                 [("Load layers", self.ws.load_layers), ("Ask the assistant", self.show_assistant)]))
        lay.addWidget(self._card("Prepare a FINALVERSE scene", "A typed processing plan you review before anything runs, then an export the world engine can render.",
                                 [("Prepare plan", self.ws.make_plan), ("Preview in FINALVERSE", self.preview_in_finalverse)]))
        lay.addWidget(self._card("Publish to SpatialDB", "Reviewed scenes only, with your approval. Publication never changes a living world.",
                                 [("Publish reviewed scene", self._approve_publish)]))
        recent = QListWidget()
        recent.setMaximumHeight(110)
        for p in (QgsSettings().value("UI/recentProjects", []) or [])[:5] if isinstance(QgsSettings().value("UI/recentProjects", []), list) else []:
            recent.addItem(str(p))
        if recent.count() == 0:
            recent.addItem("No recent projects yet")
        lab = QLabel("Recent projects")
        lab.setObjectName("fgSub")
        lay.addWidget(lab)
        lay.addWidget(recent)
        foot = QLabel("Built on the open-source QGIS project (GPL). The full QGIS toolset stays one shortcut away: Ctrl+Alt+M.")
        foot.setObjectName("fgSub")
        foot.setWordWrap(True)
        lay.addWidget(foot)
        lay.addStretch(1)
        self.home.setWidget(w)
        self.home.setMinimumWidth(340)
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.home)
        self.home.setVisible(False)

    def _approve_publish(self):
        if QMessageBox.question(self.window, "Publish to SpatialDB", "Publish the reviewed scene through the operator's publication adapter? This needs your approval and never changes a living world.") == QMessageBox.StandardButton.Yes:
            self.ws.publish_scene()

    # ------------------------------------------------------------------ contextual tools
    def _build_context(self):
        self.context = QToolBar("FinalGIS Context", self.window)
        self.context.setObjectName("FinalGISContextToolBar")
        self.window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.context)
        self.context.setVisible(False)
        self._refresh_context(None)

    def _refresh_context(self, layer):
        tb = self.context
        tb.clear()
        lab = QLabel("  ")
        tb.addWidget(lab)
        if layer is None:
            lab.setText("  No layer selected · ")
            if hasattr(self.iface, "openDataSourceManagerPage"):
                tb.addAction("Add data…", lambda: self.iface.openDataSourceManagerPage(""))
            tb.addAction("Load Montréal", self.ws.load_layers)
            return
        kind = layer.type()
        crs = layer.crs().authid() or "no CRS"
        if kind == QgsMapLayerType.VectorLayer:
            geom = QgsWkbTypes.geometryDisplayString(layer.geometryType())
            lab.setText(f"  {layer.name()} · {geom} · {layer.featureCount()} features · {crs}  ")
            tb.addAction("Zoom to layer", lambda: self.iface.zoomToActiveLayer())
            tb.addAction("Attribute table", lambda: self.iface.showAttributeTable(layer))
            tb.addAction("Validate geometry", lambda: self.ask("Validate the current layer"))
            tb.addAction("Style…", lambda: self.iface.showLayerProperties(layer, "mOptsPage_Style"))
        else:
            lab.setText(f"  {layer.name()} · raster · {layer.width()}×{layer.height()} px · {crs}  ")
            tb.addAction("Zoom to layer", lambda: self.iface.zoomToActiveLayer())
            tb.addAction("Properties…", lambda: self.iface.showLayerProperties(layer))
        tb.addSeparator()
        tb.addAction("Ask AI about this layer", lambda: self.ask(f"Describe the layer {layer.name()}"))

    # ------------------------------------------------------------------ AI GIS assistant
    def _build_assistant(self):
        self.assistant = QDockWidget("AI GIS Assistant", self.window)
        self.assistant.setObjectName("FinalGISAssistant")
        w = QWidget()
        lay = QVBoxLayout(w)
        self.ask_box = QLineEdit()
        self.ask_box.setPlaceholderText("Ask about your data: datasets, CRS, validity, styling, scene preparation…")
        self.ask_box.returnPressed.connect(lambda: self.ask(self.ask_box.text()))
        lay.addWidget(self.ask_box)
        legend = QLabel("<span style='color:#63d6a0'>■ verified by QGIS</span> &nbsp; <span style='color:#c9b6ff'>■ AI proposal (not applied)</span>")
        lay.addWidget(legend)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        lay.addWidget(self.output)
        row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply proposal…")
        self.apply_btn.setObjectName("fgPrimary")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_proposal)
        row.addWidget(self.apply_btn)
        row.addStretch(1)
        lay.addLayout(row)
        self.assistant.setWidget(w)
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.assistant)
        self.assistant.setVisible(False)
        self.pending = None

    def show_assistant(self):
        self.assistant.setVisible(True)
        self.assistant.raise_()
        self.ask_box.setFocus()

    def _facts(self):
        project = QgsProject.instance()
        facts = {"project_crs": project.crs().authid(), "layers": []}
        for layer in project.mapLayers().values():
            d = {"name": layer.name(), "crs": layer.crs().authid(), "type": "vector" if layer.type() == QgsMapLayerType.VectorLayer else "raster"}
            if d["type"] == "vector":
                d["features"] = layer.featureCount()
                d["geometry"] = QgsWkbTypes.geometryDisplayString(layer.geometryType())
                d["fields"] = [f.name() for f in layer.fields()][:20]
            e = layer.extent()
            d["extent"] = [round(e.xMinimum(), 3), round(e.yMinimum(), 3), round(e.xMaximum(), 3), round(e.yMaximum(), 3)]
            facts["layers"].append(d)
        return facts

    def ask(self, text):
        self.show_assistant()
        text = (text or "").strip()
        if not text:
            return
        self.ask_box.setText(text)
        low = text.lower()
        facts = self._facts()
        out = [f"› {text}"]
        self.pending = None
        self.apply_btn.setEnabled(False)
        if "crs" in low:
            out.append("VERIFIED BY QGIS · CRS inspection")
            for l in facts["layers"]:
                flag = "" if l["crs"] == facts["project_crs"] else "  ← differs from the project CRS (reprojected on the fly)"
                out.append(f"  {l['name']}: {l['crs'] or 'undefined'}{flag}")
            out.append(f"  project: {facts['project_crs']}")
        elif "valid" in low:
            layer = self.iface.activeLayer()
            if layer is None or layer.type() != QgsMapLayerType.VectorLayer:
                out.append("Select a vector layer to validate.")
            else:
                try:
                    import processing
                    r = processing.run("native:checkvalidity", {"INPUT_LAYER": layer, "METHOD": 2, "VALID_OUTPUT": "memory:", "INVALID_OUTPUT": "memory:", "ERROR_OUTPUT": "memory:"})
                    out.append("VERIFIED BY QGIS · native:checkvalidity (GEOS), read-only")
                    out.append(f"  {layer.name()}: {r.get('VALID_COUNT', '?')} valid, {r.get('INVALID_COUNT', '?')} invalid, {r.get('ERROR_COUNT', '?')} errors")
                except Exception as e:  # report, never invent a result
                    out.append(f"Validation could not run: {e}")
        elif any(k in low for k in ("what data", "datasets", "discover", "describe")):
            out.append("VERIFIED BY QGIS · project inventory")
            for l in facts["layers"]:
                extra = f", {l.get('features')} {l.get('geometry', '')} features" if l["type"] == "vector" else ""
                out.append(f"  {l['name']} ({l['type']}, {l['crs']}{extra})")
            if not facts["layers"]:
                out.append("  The project has no layers yet. Try 'Load verified Montréal layers'.")
        else:
            out.append("AI PROPOSAL · asking the local model (gemma4:e4b); nothing will be applied without your approval…")
            self._ask_model(text, facts)
        self.output.setPlainText("\n".join(out))

    def _ask_model(self, text, facts):
        def run():
            prompt = ("You are a GIS assistant. Using ONLY these project facts, propose at most one concrete action as JSON "
                      "{\"summary\": str, \"action\": \"style_categorized\"|\"none\", \"layer\": str, \"field\": str}. "
                      f"Facts: {json.dumps(facts)[:6000]}\nRequest: {text}")
            body = json.dumps({"model": "gemma4:e4b", "prompt": prompt, "stream": False, "format": "json", "think": False,
                               "options": {"temperature": 0, "num_predict": 300}, "keep_alive": "60m"}).encode()
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(urllib.request.Request("http://127.0.0.1:11434/api/generate", body, {"Content-Type": "application/json"}), timeout=90) as r:
                    self.worker.done.emit("ok", json.loads(r.read())["response"])
            except Exception as e:
                self.worker.done.emit("error", repr(e))
        threading.Thread(target=run, daemon=True).start()

    def _assistant_result(self, kind, text):
        lines = self.output.toPlainText().splitlines()
        if kind != "ok":
            lines.append(f"The local model is unavailable ({text}); no proposal.")
        else:
            try:
                p = json.loads(text)
            except json.JSONDecodeError:
                p = {"summary": text[:400], "action": "none"}
            lines.append("AI PROPOSAL (not applied): " + str(p.get("summary", ""))[:600])
            layer = next((l for l in QgsProject.instance().mapLayersByName(p.get("layer", ""))), None)
            if p.get("action") == "style_categorized" and layer and layer.type() == QgsMapLayerType.VectorLayer and layer.fields().indexOf(p.get("field", "")) >= 0:
                self.pending = (layer, p["field"])
                lines.append(f"  Proposed: categorized style of '{layer.name()}' by '{p['field']}'. Press 'Apply proposal…' to review and apply.")
                self.apply_btn.setEnabled(True)
            elif p.get("action") not in (None, "none"):
                lines.append("  The proposal does not match a layer/field in this project and is not offered for applying.")
        self.output.setPlainText("\n".join(lines))

    def _apply_proposal(self):
        if not self.pending:
            return
        layer, field = self.pending
        if QMessageBox.question(self.window, "Apply AI proposal", f"Change the style of '{layer.name()}' to categories of '{field}'? You can undo it in the layer properties.") != QMessageBox.StandardButton.Yes:
            return
        from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSymbol
        idx = layer.fields().indexOf(field)
        cats = []
        for v in sorted(layer.uniqueValues(idx), key=str)[:24]:
            s = QgsSymbol.defaultSymbol(layer.geometryType())
            cats.append(QgsRendererCategory(v, s, str(v)))
        r = QgsCategorizedSymbolRenderer(field, cats)
        from qgis.core import QgsStyle
        r.updateColorRamp(QgsStyle.defaultStyle().colorRamp("Spectral"))
        layer.setRenderer(r)
        layer.triggerRepaint()
        self.output.appendPlainText(f"APPLIED BY YOU · categorized style on '{layer.name()}' ({len(cats)} categories).")
        self.pending = None
        self.apply_btn.setEnabled(False)

    # ------------------------------------------------------------------ FINALVERSE preview
    def preview_in_finalverse(self):
        script = os.environ.get("FINALVERSE_LAUNCHER", "/Users/wenyan/Finalverse/dev/omega-xix-20261123/finalverse.sh")
        if not pathlib.Path(script).exists():
            self.iface.messageBar().pushMessage("FinalGIS", "The FINALVERSE launcher is not configured (FINALVERSE_LAUNCHER).", Qgis.MessageLevel.Warning, 6)
            return
        from qgis.PyQt.QtCore import QProcess
        QProcess.startDetached("/bin/zsh", [script, "viewer"])
        self.iface.messageBar().pushMessage("FinalGIS", "Opening the published scene in the FINALVERSE Viewer…", Qgis.MessageLevel.Info, 5)
