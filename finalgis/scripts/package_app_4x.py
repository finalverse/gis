#!/usr/bin/env python3
"""Assemble a separate FinalGIS 4.x preview desktop around a source-built QGIS 4.2.3
QGIS.app (Ω-XVIII). Local development packaging: links the Homebrew Qt 6.12 / Python
3.15 runtime it was built against, ad-hoc signed, not notarized, not portable.

Never modifies the existing FinalGIS.app (3.44.15), the user's QGIS profiles, the QGIS
source tree or the installed QGIS.app it copies from. The engine binary is copied
byte-for-byte; only the bundle identity, launcher, icon, notices and an isolated
profile with the FinalGIS plugin are added.

    package_app_4x.py --qgis QGIS.app --product BRANDING/finalgis --source-tree QGIS_SRC \
        --worker finalgis-worker --data MONTREAL_DIR --output FinalGIS-4.2.3-preview.app --profile DIR
"""
import argparse, hashlib, json, os, pathlib, plistlib, shutil, subprocess


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def run(args, **kw):
    subprocess.run(list(map(str, args)), check=True, **kw)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for n in ["qgis", "product", "source-tree", "worker", "data", "output", "profile"]:
        p.add_argument("--" + n, type=pathlib.Path, required=True)
    p.add_argument("--rpath", action="append", default=[], help="extra absolute library directory the source build links (repeatable)")
    p.add_argument("--python", type=pathlib.Path, default=pathlib.Path("/opt/homebrew/opt/python@3.15/bin/python3.15"))
    p.add_argument("--python-home", default="/opt/homebrew/opt/python@3.15/Frameworks/Python.framework/Versions/3.15")
    p.add_argument("--tools-path", type=pathlib.Path, help="directory with the GDAL command-line tools matching the linked GDAL (gdal: Processing provider)")
    p.add_argument("--python-site", type=pathlib.Path, help="private site directory with osgeo, psycopg2 and Processing's pure-Python dependencies")
    a = p.parse_args()
    os.umask(0o077)
    app, profile, foundation = a.output.resolve(), a.profile.resolve(), a.qgis.resolve()
    if app.exists() or profile.exists():
        raise SystemExit("new app and profile destinations required")
    info = plistlib.loads((foundation / "Contents/Info.plist").read_bytes())
    version = info.get("CFBundleShortVersionString", "")
    if not version.startswith("4.2.3"):
        raise SystemExit(f"expected a QGIS 4.2.3 foundation, found {version!r}")
    original = foundation / "Contents/MacOS" / info["CFBundleExecutable"]
    original_sha = sha(original)
    original_code = subprocess.run(["otool", "-tV", str(original)], capture_output=True).stdout
    app.mkdir(parents=True)
    run(["cp", "-cR", foundation / "Contents", app / "Contents"])  # an install prefix also holds include/ at its root
    # codesign treats a dotted directory in Contents/Frameworks as a nested bundle; the
    # pip metadata of the qgis package is not needed at runtime, keep it under Resources.
    for d in (app / "Contents/Frameworks").glob("*.dist-info"):
        (app / "Contents/Resources/qgis/python-metadata").mkdir(parents=True, exist_ok=True)
        d.rename(app / "Contents/Resources/qgis/python-metadata" / d.name)
    mac = app / "Contents/MacOS"
    engine = mac / "FinalGIS-engine"
    (mac / info["CFBundleExecutable"]).rename(engine)
    res = app / "Contents/Resources/FinalGIS"
    (res / "native").mkdir(parents=True)
    plugin_dir = profile / "profiles/FinalGIS/python/plugins/finalgis"
    plugin_dir.parent.mkdir(parents=True)
    profile.chmod(0o700)
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(a.product / "plugin", plugin_dir, ignore=ignore)
    shutil.copytree(a.product / "plugin", res / "plugin", ignore=ignore)
    settings = profile / "profiles/FinalGIS/qgis.org"  # QGIS 4: organisation directory qgis.org
    settings.mkdir(parents=True)
    # QGIS 4 keeps profile settings in qgis.org/QGIS4.ini (verified in the running app).
    (settings / "QGIS4.ini").write_text("[PythonPlugins]\nfinalgis=true\nprocessing=true\n[locale]\noverrideFlag=true\nuserLocale=en_US\n")
    shutil.copytree(a.data, res / "data/montreal")
    # The install tree carries no build rpaths: add bundle-relative ones (and the external
    # library directories this local build links) to every Mach-O that uses @rpath.
    frameworks = app / "Contents/Frameworks"
    patched = []
    for f in sorted(app.rglob("*")):
        if not f.is_file() or f.is_symlink() or f.read_bytes()[:4] not in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
            continue
        deps = subprocess.run(["otool", "-L", str(f)], capture_output=True, text=True).stdout
        if "@rpath/" not in deps:
            continue
        have = subprocess.run(["otool", "-l", str(f)], capture_output=True, text=True).stdout
        for rp in ["@loader_path/" + os.path.relpath(frameworks, f.parent)] + [str(x) for x in a.rpath]:
            if f" path {rp} " not in have:
                run(["install_name_tool", "-add_rpath", rp, f], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run(["codesign", "--force", "--sign", "-", f], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        patched.append(str(f.relative_to(app)))
    # Splash artwork rendered with the bundle's own Qt/PyQt (the product script predates PyQt6 enums).
    shim = ("import enum,runpy,sys;from qgis.PyQt.QtGui import QImage,QPainter,QFont\n"
            "for c in (QImage,QPainter,QFont):\n"
            " for n in dir(c):\n"
            "  e=getattr(c,n)\n"
            "  if isinstance(e,type) and issubclass(e,enum.Enum):\n"
            "   [setattr(c,m.name,m) for m in e if not hasattr(c,m.name)]\n"
            "sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')")
    run([a.python, "-c", shim, a.product / "scripts/render_branding.py", a.product / "plugin/logo.png", res / "branding"],
        env=dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(frameworks)))
    shutil.copy2(a.worker, res / "native/finalgis-worker")
    lib = a.worker.parent / "libfinalgis_geo.dylib"
    if lib.is_file():
        shutil.copy2(lib, res / "native/libfinalgis_geo.dylib")
        run(["install_name_tool", "-add_rpath", "@executable_path", res / "native/finalgis-worker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (res / "finalgis-config.json").write_text(json.dumps({"bundle_relative": True, "outputs": str(profile / "exports"), "package_version": "0.3.0-preview", "foundation": "QGIS 4.2.3"}))
    (res / "notices").mkdir()
    shutil.copy2(a.source_tree / "COPYING", res / "notices/COPYING")
    lic = a.product / "docs/FINALGIS-LICENSING.md"
    if lic.is_file():
        shutil.copy2(lic, res / "notices/FOUNDATION-LICENSES.md")
    shutil.copy2(a.product / "branding/FinalGIS.icns", app / "Contents/Resources/FinalGIS.icns")
    run(["clang", "-std=c17", "-Os", "-Wall", "-Wextra", "-Werror", "-DFINALGIS_QGIS4", "-DFINALGIS_PROFILE=" + json.dumps(str(profile)),
         a.product / "product/launcher.c", "-o", mac / "FinalGIS"])
    info.update(CFBundleName="FinalGIS", CFBundleDisplayName="FinalGIS", CFBundleIdentifier="org.finalverse.finalgis.preview4",
                CFBundleExecutable="FinalGIS", CFBundleShortVersionString="0.3.0", CFBundleVersion="3",
                CFBundleGetInfoString="FinalGIS 0.3.0 preview — based on QGIS 4.2.3 (source build, Qt 6.12)",
                CFBundleIconFile="FinalGIS.icns",
                NSHumanReadableCopyright="FinalGIS product layer © Finalverse. Based on QGIS © QGIS contributors, GPL-2.0-or-later.")
    info.pop("CFBundleURLTypes", None)
    # A QGIS mac bundle points Python at Contents/Frameworks (where an official bundle ships
    # its own interpreter). This preview links Homebrew Python, so name its home explicitly;
    # the launcher passes the environment on to the engine.
    pypath = [str(app / "Contents/Frameworks")] + ([str(a.python_site.resolve())] if a.python_site else [])
    info["LSEnvironment"] = {"PYTHONHOME": a.python_home, "PYTHONPATH": os.pathsep.join(pypath), "PYTHONNOUSERSITE": "1"}
    if a.tools_path:
        info["LSEnvironment"]["PATH"] = f"{a.tools_path.resolve()}:/usr/bin:/bin:/usr/sbin:/sbin"
    for item in info.get("CFBundleDocumentTypes", []):
        item["LSHandlerRank"] = "Alternate"
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    # Only load commands (LC_RPATH) were added: the engine's machine code is unchanged.
    assert subprocess.run(["otool", "-tV", str(engine)], capture_output=True).stdout.replace(str(engine).encode(), b"") == \
        original_code.replace(str(original).encode(), b""), "engine code must be unchanged"
    for f in (res / "native").iterdir():
        run(["codesign", "--force", "--sign", "-", f], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run(["codesign", "--force", "--sign", "-", "--identifier", "org.finalverse.finalgis.engine", engine], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run(["codesign", "--force", "--deep", "--sign", "-", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    receipt = {"schema": "finalgis.desktop-package/3", "application": str(app), "foundation": str(foundation), "foundation_version": version,
               "version": "0.3.0-preview", "profile": str(profile), "engine_original_sha256": original_sha, "engine_signed_sha256": sha(engine),
               "launcher_sha256": sha(mac / "FinalGIS"), "rpath_patched_binaries": len(patched),
               "engine_text_unchanged": True, "external_library_dirs": [str(x) for x in a.rpath], "python": "Homebrew python@3.15 + PyQt6 6.12.1 (linked, not bundled)", "python_environment": info["LSEnvironment"],
               "signing": "local ad-hoc; not notarized", "portable_distribution_verified": False,
               "replaces_finalgis_app": False}
    (app.parent / (app.stem + "-package.json")).write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=1))


if __name__ == "__main__":
    main()
