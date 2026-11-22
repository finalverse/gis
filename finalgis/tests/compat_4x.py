#!/usr/bin/env python3
"""FinalGIS 4.x compatibility suite against a source-built QGIS 4.2.3 with Python
bindings (Ω-XVIII). Runs in a private profile; never touches the user's profiles.

    compat_4x.py QGIS_APP FIXTURE_DIR OUT_DIR

Checks: qgis_process version and providers (incl. the Python-based gdal/qgis providers),
native algorithms on the Montréal buildings fixture with the CRS declared explicitly
(EPSG:2950; the GeoJSON carries projected MTM8 coordinates despite its implied WGS84),
a Python-provider algorithm, PyQGIS in the app's interpreter (layer load, CRS transform
through PROJ, geometry engine), and loading the FinalGIS plugin with QGIS 4 Python.
"""
import json, os, pathlib, subprocess, sys, tempfile, time

app, fixtures, out = map(pathlib.Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
macos = app / "Contents/MacOS"
qp = macos / "bin/qgis_process" if (macos / "bin/qgis_process").exists() else macos / "qgis_process"
profile = pathlib.Path(tempfile.mkdtemp(prefix="finalgis-compat-"))
import plistlib
lsenv = plistlib.loads((app / "Contents/Info.plist").read_bytes()).get("LSEnvironment", {})  # what the desktop app gets
env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PROJ_NETWORK="OFF", QGIS_CUSTOM_CONFIG_PATH=str(profile), **lsenv)
src = f"{fixtures}/buildings.geojson|layername=buildings"
results, t_all = {}, time.time()


def proc(*args, timeout=300):
    t = time.time()
    r = subprocess.run([str(qp), "--json", *args], capture_output=True, text=True, env=env, timeout=timeout)
    try:
        data = json.loads(r.stdout[r.stdout.find("{"):]) if "{" in r.stdout else {}
    except json.JSONDecodeError:
        data = {}
    return r.returncode, data, r.stderr[-800:], round(time.time() - t, 2)


def check(name, ok, detail):
    results[name] = {"passed": bool(ok), "detail": detail}
    print(("PASS " if ok else "FAIL ") + name + f"  {json.dumps(detail)[:180]}")


v =subprocess.run([str(qp), "--version"], capture_output=True, text=True, env=env)
check("version", "4.2.3" in v.stdout, v.stdout.strip().splitlines()[:2])
rc, d, err, s = proc("list")
providers = sorted(d.get("providers", {}).keys())
check("providers incl. Python providers", rc == 0 and "native" in providers and "gdal" in providers, {"providers": providers, "seconds": s})
algs = sum(len(p.get("algorithms", {})) for p in d.get("providers", {}).values())
results["algorithm_count"] = algs

# The GeoJSON carries MTM8 metres without a crs member (GeoJSON implies WGS 84): declare it first.
rc, d, err, s_ = proc("run", "native:assignprojection", "--INPUT=" + src, "--CRS=EPSG:2950", "--OUTPUT=" + str(out / "mtm8.gpkg"))
check("native:assignprojection (declare EPSG:2950)", rc == 0 and d.get("results"), {"seconds": s_, "stderr": err[-200:] if rc else ""})
src = str(out / "mtm8.gpkg")
cases = [
    ("native:buffer", ["--INPUT=" + src, "--DISTANCE=5", "--SEGMENTS=8", "--OUTPUT=" + str(out / "buffer.gpkg")], 45),
    ("native:centroids", ["--INPUT=" + src, "--OUTPUT=" + str(out / "centroids.gpkg")], 45),
    ("native:reprojectlayer", ["--INPUT=" + src, "--TARGET_CRS=EPSG:4326", "--OUTPUT=" + str(out / "wgs84.gpkg")], 45),
    ("native:fixgeometries", ["--INPUT=" + src, "--OUTPUT=" + str(out / "fixed.gpkg")], 45),
    ("gdal:convertformat", ["--INPUT=" + src, "--OUTPUT=" + str(out / "converted.shp")], None),
]
for alg, args, expect in cases:
    rc, d, err, s = proc("run", alg, "--PROJECT_PATH=", "--ELLIPSOID=EPSG:7019", *args)
    res = d.get("results", {})
    check(alg, rc == 0 and bool(res), {"seconds": s, "results": {k: v for k, v in res.items() if not isinstance(v, (list, dict))}, "stderr": err[-200:] if rc else ""})

# PyQGIS in the app's own Python (Homebrew 3.15 + PyQt6 6.12.1).
py = r'''
import json, sys
from qgis.core import (QgsApplication, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsProject, QgsPointXY, QgsGeometry, Qgis)
QgsApplication.setPrefixPath(sys.argv[1], True)
qa = QgsApplication([], False); qa.initQgis()
lyr = QgsVectorLayer(sys.argv[2] + "/buildings.geojson", "buildings", "ogr")
lyr.setCrs(QgsCoordinateReferenceSystem("EPSG:2950"))  # declared explicitly (MTM8 coordinates)
ext = lyr.extent()
tr = QgsCoordinateTransform(lyr.crs(), QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
c = tr.transform(QgsPointXY(ext.center()))
areas = sorted(f.geometry().area() for f in lyr.getFeatures())
u = QgsGeometry.unaryUnion([f.geometry() for f in lyr.getFeatures()])
sys.path.insert(0, sys.argv[3])
import importlib
plugin_ok, plugin_err = True, ""
try:
    import finalgis, finalgis.workspace, finalgis.identity  # FinalGIS plugin modules under QGIS 4 / PyQt6
    assert callable(finalgis.classFactory)
except Exception as e:
    plugin_ok, plugin_err = False, repr(e)[:300]
outs = {}
for n in ("buffer", "centroids", "wgs84", "fixed"):
    o = QgsVectorLayer(sys.argv[4] + "/" + n + ".gpkg", n, "ogr")
    outs[n] = {"valid": o.isValid(), "features": o.featureCount(), "crs": o.crs().authid(),
               "extent": [round(v, 4) for v in (o.extent().xMinimum(), o.extent().yMinimum(), o.extent().xMaximum(), o.extent().yMaximum())]}
print(json.dumps({"outputs": outs, "qgis": Qgis.version(), "python": sys.version.split()[0], "valid": lyr.isValid(), "features": lyr.featureCount(),
                  "crs": lyr.crs().authid(), "center_lonlat": [round(c.x(), 6), round(c.y(), 6)], "min_area": round(areas[0], 3),
                  "max_area": round(areas[-1], 3), "union_valid": u.isGeosValid(), "plugin_import": plugin_ok, "plugin_error": plugin_err}))
qa.exitQgis()
'''
pyexe = os.environ.get("FINALGIS_PYTHON", "/opt/homebrew/opt/python@3.15/bin/python3.15")
pyenv = dict(env, PYTHONPATH=os.pathsep.join([env.get("PYTHONPATH", str(app / "Contents/Frameworks")), str(app / "Contents/Resources/qgis/python"), str(app / "Contents/Resources/qgis/python/plugins")]))
pyenv.pop("PYTHONHOME", None)  # the test interpreter is Homebrew Python itself
r = subprocess.run([pyexe, "-c", py, str(app / "Contents/MacOS"), str(fixtures), sys.argv[4] if len(sys.argv) > 4 else str(fixtures), str(out)],
                   capture_output=True, text=True, env=pyenv, timeout=300)
try:
    pq = json.loads(r.stdout.strip().splitlines()[-1])
except Exception:
    pq = {"stdout": r.stdout[-500:], "stderr": r.stderr[-800:]}
check("pyqgis layer + CRS + PROJ + GEOS", pq.get("valid") and pq.get("features") == 45 and pq.get("crs") == "EPSG:2950"
      and -74 < pq.get("center_lonlat", [0, 0])[0] < -73 and 45 < pq.get("center_lonlat", [0, 0])[1] < 46 and pq.get("union_valid"), pq)
o = pq.get("outputs", {})
check("algorithm outputs (45 features each; WGS 84 output inside Montréal)", all(v.get("valid") and v.get("features") == 45 for v in o.values()) and len(o) == 4
      and o["wgs84"]["crs"] == "EPSG:4326" and -73.7 < o["wgs84"]["extent"][0] < o["wgs84"]["extent"][2] < -73.4, o)
check("finalgis plugin imports under QGIS 4 Python", pq.get("plugin_import") is True, {"error": pq.get("plugin_error")})
summary = {"passed": sum(1 for v in results.values() if isinstance(v, dict) and v.get("passed")),
           "total": sum(1 for v in results.values() if isinstance(v, dict) and "passed" in v), "algorithms": algs,
           "seconds": round(time.time() - t_all, 1), "results": results}
(out / "compat-4x.json").write_text(json.dumps(summary, indent=1))
print(json.dumps({k: summary[k] for k in ("passed", "total", "algorithms", "seconds")}))
