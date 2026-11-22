#!/usr/bin/env python3
"""Loopback authenticated preview adapter; WMS execution belongs to MapServer."""

import argparse
import hashlib
import hmac
import json
import math
import os
import secrets
import subprocess
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ["mapserv", "source", "out", "publication"]:
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--seconds", type=int, default=120)
    a = p.parse_args()
    os.umask(0o077)
    if not 1 <= a.seconds <= 590:
        raise ValueError("bounded duration required")
    a.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    files = {
        name: a.source / file
        for name, file in [
            ("roofs", "buildings.geojson"),
            ("roads", "roads.geojson"),
            ("terrain", "dtm.tif"),
        ]
    }
    for file in files.values():
        if (
            file.is_symlink()
            or not file.is_file()
            or '"' in str(file)
            or "\n" in str(file)
        ):
            raise ValueError("unsafe source")
    hashes = {name: sha(file) for name, file in files.items()}
    version = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    pub = json.loads(a.publication.read_text())
    if pub["stage"] != "PUBLISHED":
        raise ValueError("persisted publication reference required")
    token = secrets.token_hex(32)
    (a.out / "token").write_text(token)
    cache = OrderedDict()
    extent = [300489.334946641, 5040679.30754108, 300749.334946641, 5040939.30754108]
    mapfile = a.out / "montreal.map"
    config = a.out / "mapserver.conf"
    layers = []
    for name, file in files.items():
        raster = name == "terrain"
        kind = "RASTER" if raster else "POLYGON" if name == "roofs" else "LINE"
        datasource = (
            f'DATA "{file.resolve()}"'
            if raster
            else f'CONNECTIONTYPE OGR CONNECTION "{file.resolve()}" DATA "{file.stem}"'
        )
        style = (
            ""
            if raster
            else "CLASS STYLE "
            + (
                "COLOR 188 128 87 OUTLINECOLOR 73 63 59"
                if name == "roofs"
                else "COLOR 36 132 155 WIDTH 2"
            )
            + " END END"
        )
        crs = 3979 if raster else 2950 if name == "roofs" else 4326
        layers.append(
            f'LAYER NAME "{name}" TYPE {kind} STATUS ON {datasource} PROJECTION "init=epsg:{crs}" END METADATA "wms_title" "{name}" END {style} END'
        )
    mapfile.write_text(
        'MAP NAME "FinalGIS" SIZE 512 512 MAXSIZE 1024 EXTENT '
        + " ".join(map(str, extent))
        + ' UNITS METERS PROJECTION "init=epsg:2950" END IMAGETYPE "png" OUTPUTFORMAT NAME "png" DRIVER "AGG/PNG" MIMETYPE "image/png" IMAGEMODE RGB END WEB METADATA "ows_title" "FinalGIS Montreal Preview" "ows_enable_request" "GetMap GetCapabilities" "ows_srs" "EPSG:2950 EPSG:4326" "ows_onlineresource" "http://127.0.0.1/wms?" END END '
        + " ".join(layers)
        + " END"
    )
    config.write_text(
        f'CONFIG ENV MS_MAP_NO_PATH "1" END MAPS montreal "{mapfile.resolve()}" END END'
    )
    catalog = {
        "schema": "finalgis.map-catalog/1",
        "dataset_version": version,
        "sources": hashes,
        "layers": list(files),
        "crs": ["EPSG:2950", "EPSG:4326"],
        "extent_2950": extent,
        "wms_version": "1.1.1",
        "publication_reference": pub["identity"],
        "registration_status": "2D geographic source projection; no resident/world-state registration",
        "world_mutated": False,
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, body, kind="application/json", extra=None):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not hmac.compare_digest(
                self.headers.get("Authorization", ""), "Bearer " + token
            ):
                self.respond(401, b'{"error":"unauthorized"}')
                return
            if any(sha(file) != hashes[name] for name, file in files.items()):
                self.respond(409, b'{"error":"source changed"}')
                return
            url = urlsplit(self.path)
            if url.path == "/catalog":
                self.respond(200, json.dumps(catalog).encode())
                return
            if url.path != "/wms" or len(self.path) > 4096:
                self.respond(404, b"{}")
                return
            pairs = parse_qsl(url.query, keep_blank_values=True)
            q = {k.upper(): v for k, v in pairs}
            allowed = {
                "SERVICE",
                "VERSION",
                "REQUEST",
                "LAYERS",
                "STYLES",
                "SRS",
                "BBOX",
                "WIDTH",
                "HEIGHT",
                "FORMAT",
                "TRANSPARENT",
            }
            try:
                if (
                    len(q) != len(pairs)
                    or set(q) - allowed
                    or q.get("SERVICE") != "WMS"
                    or q.get("VERSION") != "1.1.1"
                    or q.get("REQUEST") not in ["GetMap", "GetCapabilities"]
                ):
                    raise ValueError("request schema")
                if q["REQUEST"] == "GetMap":
                    if q.get("SRS") not in catalog["crs"]:
                        raise ValueError("unsupported CRS")
                    if any(x not in files for x in q.get("LAYERS", "").split(",")):
                        self.respond(404, b'{"error":"unknown layer"}')
                        return
                    w, h = int(q["WIDTH"]), int(q["HEIGHT"])
                    box = list(map(float, q["BBOX"].split(",")))
                    if (
                        not 1 <= w <= 1024
                        or not 1 <= h <= 1024
                        or len(box) != 4
                        or not all(math.isfinite(x) for x in box)
                        or box[0] >= box[2]
                        or box[1] >= box[3]
                        or q.get("FORMAT") != "image/png"
                        or q.get("STYLES", "") != ""
                    ):
                        raise ValueError("map bounds/format")
                    if q["SRS"] == "EPSG:2950" and (
                        box[0] < extent[0] - 1
                        or box[1] < extent[1] - 1
                        or box[2] > extent[2] + 1
                        or box[3] > extent[3] + 1
                    ):
                        raise ValueError("outside dataset extent")
                    if q["SRS"] == "EPSG:4326" and not (
                        -74 <= box[0] < box[2] <= -73 and 45 <= box[1] < box[3] <= 46
                    ):
                        raise ValueError("outside geographic scope")
                key = hashlib.sha256(
                    (version + urlencode(sorted(q.items()))).encode()
                ).hexdigest()
                if key in cache:
                    kind, body = cache[key]
                    self.respond(200, body, kind, {"X-Cache": "HIT", "ETag": key})
                    return
                env = dict(
                    os.environ,
                    MAPSERVER_CONFIG_FILE=str(config.resolve()),
                    REQUEST_METHOD="GET",
                    QUERY_STRING=urlencode(dict(q, map="montreal")),
                    SERVER_NAME="127.0.0.1",
                    SERVER_PORT=str(self.server.server_port),
                    SCRIPT_NAME="/wms",
                    PROJ_NETWORK="OFF",
                )
                r = subprocess.run(
                    [str(a.mapserv.resolve())], env=env, capture_output=True, timeout=10
                )
                if r.returncode or len(r.stdout) > 4 * 1024 * 1024:
                    raise RuntimeError("map engine failure")
                raw = r.stdout
                separator = b"\r\n\r\n" if b"\r\n\r\n" in raw[:8192] else b"\n\n"
                headers, body = raw.split(separator, 1)
                headers = headers.replace(b"\r\n", b"\n")
                kind = next(
                    line.split(b":", 1)[1].strip().decode()
                    for line in headers.splitlines()
                    if line.lower().startswith(b"content-type:")
                )
                if q["REQUEST"] == "GetMap" and not body.startswith(b"\x89PNG"):
                    raise RuntimeError(body[:300].decode(errors="replace"))
                if (
                    sum(len(v[1]) for v in cache.values()) + len(body) > 8 * 1024 * 1024
                    or len(cache) >= 16
                ):
                    cache.clear()
                cache[key] = (kind, body)
                self.respond(200, body, kind, {"X-Cache": "MISS", "ETag": key})
            except (ValueError, KeyError):
                self.respond(400, b'{"error":"invalid bounded map request"}')
            except Exception as e:
                self.respond(502, json.dumps({"error": str(e)[:400]}).encode())

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 0.2
    (a.out / "service.json").write_text(
        json.dumps(
            {"endpoint": f"http://127.0.0.1:{server.server_port}", "catalog": catalog},
            indent=2,
        )
    )
    print("READY", flush=True)
    end = time.monotonic() + a.seconds
    while time.monotonic() < end and not (a.out / "cancel").exists():
        server.handle_request()
    server.server_close()


if __name__ == "__main__":
    main()
