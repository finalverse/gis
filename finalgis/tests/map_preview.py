import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

p = argparse.ArgumentParser()
p.add_argument("--root", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
a = p.parse_args()
root = a.root
source = a.source
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
results = []
digests = []
for episode in range(2):
    out = root / ("map-test-" + str(episode))
    log = (root / ("map-test-" + str(episode) + ".log")).open("w")
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "services/map_preview.py"),
            "--mapserv",
            str(root / "mapserver-build/mapserv"),
            "--source",
            str(source),
            "--publication",
            str(root / "final-publication/state.json"),
            "--out",
            str(out),
            "--seconds",
            "50",
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(200):
            if (out / "service.json").exists():
                break
            if proc.poll() is not None:
                raise RuntimeError("gateway startup failed")
            time.sleep(0.05)
        endpoint = json.loads((out / "service.json").read_text())["endpoint"]
        token = (out / "token").read_text()

        def get(path, auth=True):
            try:
                r = opener.open(
                    urllib.request.Request(
                        endpoint + path,
                        headers={"Authorization": "Bearer " + token} if auth else {},
                    ),
                    timeout=15,
                )
                return r.status, dict(r.headers), r.read()
            except urllib.error.HTTPError as e:
                return e.code, dict(e.headers), e.read()

        assert get("/catalog", False)[0] == 401
        catalog = get("/catalog")
        assert catalog[0] == 200
        q = {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": "roofs,roads",
            "STYLES": "",
            "SRS": "EPSG:2950",
            "BBOX": "300489.334946641,5040679.30754108,300749.334946641,5040939.30754108",
            "WIDTH": "512",
            "HEIGHT": "512",
            "FORMAT": "image/png",
        }
        first = get("/wms?" + urlencode(q))
        assert first[0] == 200 and first[2].startswith(b"\x89PNG"), first
        second = get("/wms?" + urlencode(q))
        assert second[2] == first[2] and second[1]["X-Cache"] == "HIT"
        (out / "preview.png").write_bytes(first[2])
        digests.append(hashlib.sha256(first[2]).hexdigest())
        for key, value, expected in [
            ("LAYERS", "unknown", 404),
            ("SRS", "EPSG:9999", 400),
            ("WIDTH", "4096", 400),
            ("MAP", "/etc/passwd", 400),
        ]:
            bad = dict(q)
            bad[key] = value
            assert get("/wms?" + urlencode(bad))[0] == expected
        capabilities = get(
            "/wms?"
            + urlencode(
                {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetCapabilities"}
            )
        )
        assert capabilities[0] == 200 and b"WMT_MS_Capabilities" in capabilities[2], (
            capabilities
        )
        results.append(
            {
                "real_map_png": True,
                "unauthorized_refused": True,
                "invalid_layer_crs_size_and_map_path_refused": True,
                "cache_equal": True,
                "capabilities": True,
            }
        )
    finally:
        (out / "cancel").touch()
        proc.wait(timeout=5)
        log.close()
assert digests[0] == digests[1]
(root / "map-tests.json").write_text(
    json.dumps(
        {
            "episodes": results,
            "restart_png_identical": True,
            "sha256": digests,
            "world_mutated": False,
        },
        indent=2,
    )
)
print("real MapServer WMS, access, bounds, cache and restart passed")
