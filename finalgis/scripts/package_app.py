#!/usr/bin/env python3
"""Assemble a separate FinalGIS desktop, retaining the pinned upstream engine.

Local development packaging; no notarized/portable release is implied. Never
modifies an existing app, profile, QGIS source or official foundation binary.
"""

import argparse
import hashlib
import json
import os
import pathlib
import plistlib
import re
import shutil
import subprocess
import sys


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def run(args, **kwargs):
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def code_sha(path):
    raw = subprocess.check_output(
        ["otool", "-arch", "all", "-s", "__TEXT", "__text", str(path)], text=True
    )
    instructions = []
    for line in raw.splitlines():
        parts = line.split()
        if (
            parts
            and re.fullmatch("[0-9a-fA-F]{8,16}", parts[0])
            and all(re.fullmatch("[0-9a-fA-F]+", x) for x in parts[1:])
        ):
            instructions.extend(parts[1:])
    if not instructions:
        raise ValueError("Native code section required")
    return hashlib.sha256("".join(instructions).encode()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["qgis", "worker", "source", "output", "profile"]:
        p.add_argument("--" + name, type=pathlib.Path, required=True)
    a = p.parse_args()
    os.umask(0o077)
    product = pathlib.Path(__file__).resolve().parents[1]
    app = a.output.resolve()
    profile = a.profile.resolve()
    foundation = a.qgis.resolve()
    worker = a.worker.resolve()
    if app.exists() or profile.exists():
        raise ValueError("New app and profile destinations required")
    if any(ord(c) < 32 for c in str(app) + str(profile)):
        raise ValueError("Control characters in product paths")
    info = plistlib.loads((foundation / "Contents/Info.plist").read_bytes())
    if info["CFBundleShortVersionString"] != "3.44.15":
        raise ValueError("Only pinned3.44.15 desktop foundation verified")
    original = foundation / "Contents/MacOS" / info["CFBundleExecutable"]
    if not original.is_file() or not worker.is_file():
        raise ValueError("Native foundation and built FinalGIS worker required")
    app.parent.mkdir(parents=True, exist_ok=True)
    profile.mkdir(parents=True, mode=0o700)
    run(["cp", "-cR", foundation, app])
    mac = app / "Contents/MacOS"
    engine = mac / "FinalGIS-engine"
    (mac / info["CFBundleExecutable"]).rename(engine)
    resources = app / "Contents/Resources/FinalGIS"
    resources.mkdir()
    plugins = profile / "profiles/FinalGIS/python/plugins/finalgis"
    plugins.parent.mkdir(parents=True)
    shutil.copytree(
        product / "plugin", plugins, ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(
        product / "plugin",
        resources / "plugin",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    settings = profile / "profiles/FinalGIS/qgis.org"
    settings.mkdir(parents=True)
    (settings / "QGIS3.ini").write_text(
        "[PythonPlugins]\nfinalgis=true\nprocessing=true\n[UI]\nCustomization\\enabled=true\n[locale]\noverrideFlag=true\nuserLocale=en_US\n"
    )
    shutil.copytree(a.source, resources / "data/montreal")
    (resources / "native").mkdir()
    shutil.copy2(worker, resources / "native/finalgis-worker")
    library = worker.parent / "libfinalgis_geo.dylib"
    if not library.is_file():
        raise ValueError("Native worker sibling library required")
    shutil.copy2(library, resources / "native/libfinalgis_geo.dylib")
    run(
        [
            "install_name_tool",
            "-add_rpath",
            "@executable_path",
            resources / "native/finalgis-worker",
        ],
        stdout=subprocess.DEVNULL,
    )
    for f in (resources / "native").iterdir():
        run(
            ["codesign", "--force", "--sign", "-", f],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    (resources / "finalgis-config.json").write_text(
        json.dumps(
            {
                "bundle_relative": True,
                "outputs": str(profile / "exports"),
                "package_version": "0.2.0",
            }
        )
    )
    (resources / "notices").mkdir()
    shutil.copy2(product.parent / "COPYING", resources / "notices/COPYING")
    shutil.copy2(
        product / "docs/FINALGIS-LICENSING.md",
        resources / "notices/FOUNDATION-LICENSES.md",
    )
    shutil.copy2(product / "foundation.lock.json", resources / "foundation.lock.json")
    shutil.copy2(
        product / "branding/FinalGIS.icns", app / "Contents/Resources/FinalGIS.icns"
    )
    # An actual native bundle launcher replaces the old shell wrapper that opened
    # a different QGIS.app. All paths are passed as argv, never interpreted by a shell.
    run(
        [
            "clang",
            "-std=c17",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-DFINALGIS_PROFILE=" + json.dumps(str(profile)),
            product / "product/launcher.c",
            "-o",
            mac / "FinalGIS",
        ]
    )
    info.update(
        CFBundleName="FinalGIS",
        CFBundleDisplayName="FinalGIS",
        CFBundleIdentifier="org.finalverse.finalgis",
        CFBundleExecutable="FinalGIS",
        CFBundleShortVersionString="0.2.0",
        CFBundleVersion="2",
        CFBundleGetInfoString="FinalGIS 0.2.0 — based on QGIS 3.44.15 LTR",
        CFBundleIconFile="FinalGIS.icns",
        NSHumanReadableCopyright="FinalGIS product layer © Finalverse. Based on QGIS © QGIS contributors, GPL-2.0-or-later.",
    )
    # Preserve format identifiers while avoiding taking over upstream URL handlers
    # and preferred application associations.
    info.pop("CFBundleURLTypes", None)
    for item in info.get("CFBundleDocumentTypes", []):
        item["LSHandlerRank"] = "Alternate"
    if "NSLocalNetworkUsageDescription" in info:
        info["NSLocalNetworkUsageDescription"] = (
            "FinalGIS can connect to GIS services configured by you."
        )
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    env = dict(
        os.environ,
        QT_QPA_PLATFORM="offscreen",
        PYTHONHOME=str(app / "Contents/Frameworks"),
        PYTHONPATH=os.pathsep.join(
            [
                str(app / "Contents/Resources/qgis/python"),
                str(app / "Contents/Resources/python3.11/site-packages"),
            ]
        ),
    )
    run(
        [
            app / "Contents/MacOS/python3.12",
            product / "scripts/render_branding.py",
            product / "plugin/logo.png",
            resources / "branding",
        ],
        env=env,
    )
    original_sha = sha(original)
    original_code = code_sha(original)
    assert sha(engine) == original_sha, "Pre-signing engine byte integrity"
    run(
        [
            "codesign",
            "--force",
            "--sign",
            "-",
            "--identifier",
            "org.finalverse.finalgis.engine",
            engine,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert code_sha(engine) == original_code, "Original native instructions preserved"
    run(
        ["codesign", "--force", "--sign", "-", app],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    receipt = {
        "schema": "finalgis.desktop-package/2",
        "application": str(app),
        "foundation": str(foundation),
        "foundation_version": "3.44.15",
        "version": "0.2.0",
        "profile": str(profile),
        "engine_sha256": sha(engine),
        "engine_original_sha256": original_sha,
        "engine_code_sha256": original_code,
        "engine_instructions_unchanged": True,
        "engine_signature_regenerated": True,
        "product_launcher_sha256": sha(mac / "FinalGIS"),
        "native_worker_sha256": sha(resources / "native/finalgis-worker"),
        "source_engine_rebuilt": False,
        "signing": "local ad-hoc; not notarized",
        "portable_distribution_verified": False,
    }
    (app.parent / (app.stem + "-package.json")).write_text(
        json.dumps(receipt, indent=2)
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
