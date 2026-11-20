#!/usr/bin/env python3
"""Write a Finalverse Map Server (fvmapd) deployment for a FinalGIS dataset.

Creates, in a NEW private directory: config.json, tokens.json (SHA-256 digests
only) and one private token file per principal. Paths are recorded exactly as
given (absolute); nothing is copied, and no world store is opened for writing.
"""

import argparse
import hashlib
import json
import os
import secrets
from pathlib import Path

LAYERS = [
    ("terrain", "raster", "dtm.tif", None, "EPSG:3979", {}),
    ("roofs", "polygon", "buildings.geojson", "buildings", "EPSG:2950", {"color": [188, 128, 87], "outline": [73, 63, 59]}),
    ("roads", "line", "roads.geojson", "roads", "EPSG:4326", {"color": [36, 132, 155], "width": 2}),
]
EXTENT = [300489.334946641, 5040679.30754108, 300749.334946641, 5040939.30754108]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True, help="FinalGIS Montreal dataset directory")
    p.add_argument("--mapserv", type=Path, required=True)
    p.add_argument("--proj-data", type=Path, required=True)
    p.add_argument("--publication", type=Path, help="persisted PUBLISHED publication record")
    p.add_argument("--registration", type=Path, help="finalverse.geographic-registration document (presentation)")
    p.add_argument("--world-store", type=Path, help="MutSea region store, served read-only")
    p.add_argument("--port", type=int, default=0)
    a = p.parse_args()
    os.umask(0o077)
    a.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    src = a.source.resolve()
    for _, _, f, _, _, _ in LAYERS:
        if not (src / f).is_file() or (src / f).is_symlink():
            raise SystemExit(f"missing source {f}")
    dataset = {
        "id": "montreal",
        "title": "Montreal Old Port reference",
        "crs": "EPSG:2950",
        "extent": EXTENT,
        "allowed_crs": ["EPSG:2950", "EPSG:4326", "EPSG:3857"],
        "attribution": "Ville de Montreal CC-BY-4.0; NRCan OGL-Canada-2.0",
        "layers": [dict({"name": n, "type": t, "source": str(src / f), "crs": c}, **({"source_layer": sl} if sl else {}), **style)
                   for n, t, f, sl, c, style in LAYERS],
    }
    if a.publication:
        dataset["publication"] = str(a.publication.resolve())
    if a.registration:
        dataset["registration"] = str(a.registration.resolve())
    tokens, principals = {}, []
    for name, role, ds, worlds in [("operator", "admin", ["*"], ["*"]), ("finalgis", "reader", ["montreal"], ["montreal-earth"]),
                                   ("viewer", "reader", ["montreal"], ["montreal-earth"])]:
        token = secrets.token_hex(32)
        (a.out / f"{name}.token").write_text(token)
        tokens[name] = token
        principals.append({"principal": name, "token_sha256": hashlib.sha256(token.encode()).hexdigest(), "role": role, "datasets": ds, "worlds": worlds})
    (a.out / "tokens.json").write_text(json.dumps({"schema": "finalverse.map-server-tokens/1", "principals": principals}, indent=1))
    config = {
        "schema": "finalverse.map-server-config/1",
        "listen": {"host": "127.0.0.1", "port": a.port},
        "state_dir": str((a.out / "state").resolve()),
        "tokens": str((a.out / "tokens.json").resolve()),
        "backend": {"mapserv": str(a.mapserv.resolve()), "env": {"PROJ_DATA": str(a.proj_data.resolve())}, "timeout_ms": 10000, "max_concurrency": 4},
        "limits": {"worker_threads": 8, "rate_per_second": 100, "burst": 200},
        "cache": {"max_bytes": 64 << 20, "max_entries": 4096},
        "datasets": [dataset],
    }
    if a.world_store:
        world = {"id": "montreal-earth", "title": "Montreal (Earth) resident region", "dataset": "montreal", "store": str(a.world_store.resolve())}
        if a.registration:
            world["registration"] = str(a.registration.resolve())
        config["worlds"] = [world]
    (a.out / "config.json").write_text(json.dumps(config, indent=1))
    print(json.dumps({"config": str(a.out / "config.json"), "principals": [p["principal"] for p in principals]}))


if __name__ == "__main__":
    main()
