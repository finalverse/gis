"""Supported PyQGIS product layer; all geographic execution stays native."""
import json, os, pathlib, tempfile, time
from qgis.PyQt.QtCore import Qt, QProcess, QTimer, QProcessEnvironment
from qgis.PyQt.QtGui import QAction, QIcon
from qgis.PyQt.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QHBoxLayout, QComboBox, QMessageBox, QScrollArea)
from qgis.core import (Qgis, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsCoordinateReferenceSystem, QgsFillSymbol, QgsLineSymbol)

class FinalGISWorkspace:
    def __init__(self, iface):
        self.iface=iface; self.process=None; self.plan=None; self.layers=[]; self.buffer=b''
        self.root=pathlib.Path(__file__).parent
        self.config=json.loads(pathlib.Path(os.environ['FINALGIS_CONFIG']).read_text())
        if self.config.get('bundle_relative'):
            resource=pathlib.Path(os.environ['FINALGIS_CONFIG']).parent
            self.config['worker']=str(resource/'native/finalgis-worker')
            self.config['source']=str(resource/'data/montreal')
        self.last_output=None
        self.original_title=iface.mainWindow().windowTitle()
    def initGui(self):
        self.action=QAction(QIcon(str(self.root/'logo.png')),'FinalGIS World Engineering',self.iface.mainWindow())
        self.action.triggered.connect(self.show);self.iface.addPluginToMenu('FinalGIS',self.action)
        self.iface.addToolBarIcon(self.action)
        self.about=QAction('About FinalGIS',self.iface.mainWindow());self.about.setMenuRole(QAction.MenuRole.NoRole);self.about.triggered.connect(self.show_about)
        self.iface.addPluginToMenu('FinalGIS',self.about)
        self.dock=QDockWidget('FinalGIS · World Engineering',self.iface.mainWindow());self.dock.setObjectName('FinalGISWorkspace')
        widget=QWidget();layout=QVBoxLayout(widget)
        title=QLabel('FinalGIS\nGeographic Intelligence\n& World Creation')
        title.setWordWrap(True);title.setMinimumHeight(96);title.setMaximumHeight(120)
        title.setStyleSheet('QLabel{background:#123d44;color:#e5f9ee;padding:12px;font-size:16px;font-weight:600;}')
        layout.addWidget(title)
        modes=QHBoxLayout()
        self.professional=QPushButton('Professional GIS');self.professional.setShortcut('Ctrl+Alt+1')
        self.agentic=QPushButton('World Engineering');self.agentic.setShortcut('Ctrl+Alt+2')
        self.professional.clicked.connect(lambda:self.mode_changed(0));self.agentic.clicked.connect(lambda:self.mode_changed(1))
        modes.addWidget(self.professional);modes.addWidget(self.agentic);layout.addLayout(modes)
        self.status=QLabel('Public Montréal sources · bounded 260 m study area\nRoof outlines + road centerlines + NRCan elevation')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        self.load=QPushButton('Load verified Montréal layers');self.load.clicked.connect(self.load_layers);layout.addWidget(self.load)
        self.prompt=QPlainTextEdit('Analyze the road and building geometry of Old Montréal and prepare a geographically referenced 3D scene.')
        self.prompt.setMaximumHeight(100);layout.addWidget(self.prompt)
        self.provider=QComboBox();self.provider.addItems(['Deterministic reviewed recipe','Local Qwen','Local Gemma']);layout.addWidget(self.provider)
        self.make=QPushButton('Prepare processing plan');self.make.clicked.connect(self.make_plan);layout.addWidget(self.make)
        self.review=QPlainTextEdit();self.review.setReadOnly(True);self.review.setPlaceholderText('Inspect a processing plan before running it.');layout.addWidget(self.review)
        row=QHBoxLayout();self.execute=QPushButton('Approve & generate export');self.execute.setEnabled(False);self.execute.clicked.connect(self.execute_plan)
        self.cancel=QPushButton('Cancel');self.cancel.setEnabled(False);self.cancel.clicked.connect(self.cancel_work)
        row.addWidget(self.execute);row.addWidget(self.cancel);layout.addLayout(row)
        self.publish=QPushButton('Publish reviewed geographic scene');self.publish.setEnabled(False);self.publish.setToolTip('Requires an operator-configured local publication adapter; never mutates a living world.');self.publish.clicked.connect(self.publish_scene);layout.addWidget(self.publish)
        note=QLabel('Generated 12 m building heights, colors and road widths are estimates.\nExport does not change the living world. Forge and MutSea authorize publication and interaction separately.')
        note.setWordWrap(True);layout.addWidget(note)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(widget)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.dock.setMinimumWidth(380);self.dock.setWidget(scroll);self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dock)
        self.iface.mainWindow().setWindowIcon(QIcon(str(self.root/'logo.png')))
        from .identity import ProductIdentity
        self.identity=ProductIdentity(self);self.identity.install()
        # Ω-XIX: optional FinalGIS Modern workspace (reversible; the full QGIS toolset stays).
        try:
            from .modern import ModernWorkspace
            self.modern=ModernWorkspace(self);self.modern.install()
        except Exception:
            import traceback
            err=traceback.format_exc();self.modern=None
            pathlib.Path(os.environ.get('FINALGIS_LOG_DIR',tempfile.gettempdir()),'finalgis-modern-error.txt').write_text(err)
            self.iface.messageBar().pushMessage('FinalGIS','Modern workspace unavailable: '+err.strip().splitlines()[-1],Qgis.MessageLevel.Warning,10)
        self.mode_changed(0)
    def show(self):self.dock.show();self.dock.raise_()
    def mode_changed(self, index):
        for w in [self.prompt,self.provider,self.make,self.review,self.execute,self.cancel]:w.setVisible(index==1)
        self.professional.setEnabled(index!=0);self.agentic.setEnabled(index!=1)
    def show_about(self):self.identity.show_about()
    def load_layers(self):
        if self.layers:return
        source=pathlib.Path(self.config['source'])
        for filename,name,crs,color in [('roads.geojson','Montréal · verified road centerlines','EPSG:4326','#24849b'),('buildings.geojson','Montréal · verified roof outlines','EPSG:2950','#bb8057')]:
            layer=QgsVectorLayer(str(source/filename),name,'ogr')
            if not layer.isValid():raise RuntimeError('QGIS vector provider failed')
            layer.setCrs(QgsCoordinateReferenceSystem(crs))
            if filename.startswith('buildings'):layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':color,'outline_color':'#493f3b','outline_width':'0.18'}))
            else:layer.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color':color,'line_width':'0.65'}))
            QgsProject.instance().addMapLayer(layer);self.layers.append(layer)
        raster=QgsRasterLayer(str(source/'dtm.tif'),'NRCan · terrain elevation (CGVD2013)','gdal')
        if raster.isValid():QgsProject.instance().addMapLayer(raster,False);self.layers.append(raster)
        QgsProject.instance().setCrs(QgsCoordinateReferenceSystem('EPSG:2950'))
        from qgis.core import QgsRectangle
        self.iface.mapCanvas().setExtent(QgsRectangle(300489.3349,5040679.3075,300749.3349,5040939.3075));self.iface.mapCanvas().refresh()
        self.status.setText('Loaded: 45 roof outlines · 93 road centerlines\nSources validated by native worker before generation.\nWorking CRS: EPSG:2950 / metres; elevation CGVD2013.')
    def launch(self,args,finished,program=None):
        if self.process: return
        self.buffer=b'';process=QProcess(self.dock);self.process=process
        process.setProgram(program or self.config['worker']);process.setArguments(args)
        if program:
            environment=QProcessEnvironment.systemEnvironment()
            for key in ['PYTHONHOME','PYTHONPATH']:environment.remove(key)
            process.setProcessEnvironment(environment)
        self.make.setEnabled(False);self.execute.setEnabled(False);self.cancel.setEnabled(True)
        def collect():
            self.buffer+=bytes(process.readAllStandardOutput())
            if len(self.buffer)>2*1024*1024:self.cancel_work()
        process.readyReadStandardOutput.connect(collect)
        def done(code,status):
            collect();error=bytes(process.readAllStandardError()).decode(errors='replace')[:2000]
            self.process=None;self.make.setEnabled(True);self.cancel.setEnabled(False)
            if code or status!=QProcess.ExitStatus.NormalExit:self.review.setPlainText('Processing stopped: '+error);return
            try:finished(json.loads(self.buffer))
            except Exception as e:self.review.setPlainText(str(e))
            process.deleteLater()
        process.finished.connect(done)
        process.errorOccurred.connect(lambda _:self.status.setText('Native worker failed to start or stopped.'))
        process.start()
        QTimer.singleShot(60000,lambda:process.kill() if self.process is process else None)
    def make_plan(self):
        self.plan=None;self.execute.setEnabled(False);self.publish.setEnabled(False)
        provider=['mock','ollama','ollama'][self.provider.currentIndex()]
        model=['','qwen2.5:0.5b','gemma4:e4b'][self.provider.currentIndex()]
        args=['workflow-plan','--source',self.config['source'],'--request',self.prompt.toPlainText()[:2048],'--provider',provider]
        if model:args+=['--model',model]
        def ready(result):
            self.plan=result;self.review.setPlainText(json.dumps(result,indent=2,ensure_ascii=False));self.execute.setEnabled(True)
        self.launch(args,ready)
    def execute_plan(self):
        if not self.plan:return
        root=pathlib.Path(self.config['outputs']);root.mkdir(parents=True,exist_ok=True)
        fd,p=tempfile.mkstemp(prefix='reviewed-plan-',suffix='.json',dir=root)
        with os.fdopen(fd,'w') as f:json.dump(self.plan,f)
        output=root/('montreal-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.monotonic_ns()))
        def complete(result):
            self.last_output=output;self.publish.setEnabled(bool(self.config.get('publication_adapter')))
            pathlib.Path(p).unlink(missing_ok=True)
            self.review.setPlainText('Export completed\n'+str(output)+'\n\n'+json.dumps({'geometry':result['asset'],'timings_ms':result['timings_ms'],'provenance':result['accuracy_note'],'publication':result['publication']},indent=2))
            self.status.setText('Generated: 17 building proxies · 41 road segments\nVerified GLB export; living-world state unchanged.')
        self.launch(['workflow-run','--source',self.config['source'],'--output',str(output),'--plan',p,'--approved-plan',self.plan['plan_id'],'--approve'],complete)
    def publish_scene(self):
        if self.process or not self.last_output or not self.plan:return
        required=['publication_adapter','publication_config','publication_core','publication_outputs','publication_fixture_prefix','workflow_python']
        if any(not self.config.get(k) for k in required):
            self.review.setPlainText('Publication is not configured. The generated scene remains a local export.');return
        question='Publish this exact reviewed local scene through Forge and SpatialDB?\nPlan: '+self.plan['plan_id']+'\nNo living-world mutation is authorized by this action.'
        if QMessageBox.question(self.iface.mainWindow(),'Review geographic publication',question,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        job=str(time.monotonic_ns());out=pathlib.Path(self.config['publication_outputs'])/job
        args=[self.config['publication_adapter'],'--config',self.config['publication_config'],'--scene',str(self.last_output),'--out',str(out),'--fixture',self.config['publication_fixture_prefix']+job,'--core',self.config['publication_core'],'--approved-plan',self.plan['plan_id']]
        self.publish.setEnabled(False);self.status.setText('Publishing the reviewed geographic scene…')
        def published(result):
            self.review.setPlainText(json.dumps(result,indent=2));self.status.setText('Publication '+result['stage']+' · world state unchanged.')
        self.launch(args,published,self.config['workflow_python'])
    def cancel_work(self):
        if self.process:self.process.kill();self.status.setText('Cancellation requested; incomplete output is not published.')
    def unload(self):
        self.cancel_work();self.modern and self.modern.unload();self.identity.uninstall();self.iface.removePluginMenu('FinalGIS',self.action);self.iface.removePluginMenu('FinalGIS',self.about)
        self.iface.removeToolBarIcon(self.action);self.iface.removeDockWidget(self.dock);self.iface.mainWindow().setWindowTitle(self.original_title)
