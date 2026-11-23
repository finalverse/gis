#!/usr/bin/env python3
"""FinalGIS packaging audit (Ω-XIX): is a macOS app bundle self-contained?

Walks every Mach-O in the bundle and classifies each linked library and rpath:
system (/System, /usr/lib), bundle-relative (@loader_path/@executable_path/@rpath resolved
inside the bundle), or external (anything else, e.g. /opt/homebrew or a developer tree).
Also reports LSEnvironment paths outside the bundle (Python home, site directories, tools)
and the code-signing state. A bundle is only "portable" with zero external references and a
verified signature; notarization is reported as not done unless a ticket is stapled.

    audit_bundle.py APP [--json OUT]
"""
import argparse, collections, json, os, pathlib, plistlib, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("app", type=pathlib.Path)
ap.add_argument("--json")
a = ap.parse_args()
app = a.app.resolve()
ext = collections.Counter()
ext_files = collections.defaultdict(set)
machos = 0
for f in app.rglob("*"):
    if not f.is_file() or f.is_symlink():
        continue
    with open(f, "rb") as fh:
        if fh.read(4) not in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
            continue
    machos += 1
    for line in subprocess.run(["otool", "-L", str(f)], capture_output=True, text=True).stdout.splitlines()[1:]:
        dep = line.strip().split(" (")[0]
        if dep.startswith(("/System/", "/usr/lib/", "@")):
            continue
        root = "/".join(dep.split("/")[:4])
        ext[root] += 1
        ext_files[root].add(dep)
info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
env_out = {k: v for k, v in info.get("LSEnvironment", {}).items() if any(p.startswith("/") and not p.startswith(str(app)) and not p.startswith(("/usr/", "/bin", "/sbin")) for p in v.split(":"))}
sig = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], capture_output=True, text=True)
staple = subprocess.run(["xcrun", "stapler", "validate", str(app)], capture_output=True, text=True)
report = {"schema": "finalgis.bundle-audit/0.1", "app": str(app), "macho_files": machos,
          "external_library_roots": dict(ext.most_common()), "external_libraries": {k: sorted(v)[:40] for k, v in ext_files.items()},
          "external_runtime_environment": env_out, "codesign_verified": sig.returncode == 0,
          "notarized_ticket_stapled": staple.returncode == 0,
          "portable": not ext and not env_out and sig.returncode == 0}
print(json.dumps({k: report[k] for k in ("macho_files", "external_library_roots", "external_runtime_environment", "codesign_verified", "notarized_ticket_stapled", "portable")}, indent=1))
if a.json:
    json.dump(report, open(a.json, "w"), indent=1)
