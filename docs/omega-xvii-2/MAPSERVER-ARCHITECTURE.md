# Finalverse Map Server

Implemented. Lives in Albert's fork `~/Finalverse/MapServer` (`finalverse/MapServer`), directory `finalverse/`, branch `feat/finalverse-map-server-20261120` (`f91749013dd`). MapServer's own sources are **not modified**. The product is a native gateway, `fvmapd`, in front of the unmodified `mapserv` CGI.

## As built

```text
 FinalGIS / Viewer / agents ──HTTP (loopback, bearer)──► fvmapd (C++23, Boost.Beast)
                                                          │
          ┌────────────────┬──────────────────┬──────────┴─────────┬────────────────────┐
          ▼                ▼                  ▼                    ▼                    ▼
   catalog/versions   WMS router         spatial API          World Scene API      health/metrics
   (sha256 sources,   (strict 1.1.1/     (GDAL/OGR/GEOS:      (MutSea native        (/healthz /readyz
   mapfile per        1.3.0, CRS-aware   inspect_region,      projection,           /metrics, JSON logs)
   version)           extent, canonical) find_nearby)         read-only)
          │                │
          │                ▼
          │     persistent response cache (content-verified, LRU)
          ▼                │ miss
   generated mapfiles ─────► mapserv CGI (posix_spawn, clean env, timeout, output cap, slot limit)
                             = Albert's fork 8.7-dev or upstream rel-8-6-6 (both tested)
```

Not built, deliberately: QGIS Server routing (blocked on the Qt environment; see FINALGIS-UPSTREAM.md), MapCache, WMTS/vector tiles, WFS exposure. WFS/OGC API are compiled into the fork build but the gateway refuses `SERVICE=WFS` until they are tested.

## Endpoints

| Route | Auth | Purpose |
|---|---|---|
| `GET /healthz` | none | liveness |
| `GET /readyz` | none | backend present, every dataset source still matches its digest (503 otherwise) |
| `GET /metrics` | admin | Prometheus text: requests/latency per route, backend histogram, cache hit/miss/bytes, rejections by reason, inflight, catalog generation |
| `GET /v1/catalog[/{id}]` | scoped | dataset version, per-layer sha256/bytes/CRS, extent, services, registration summary, publication reference, backend identity |
| `GET /v1/maps/{id}/wms?…` | scoped | WMS 1.1.1/1.3.0 GetMap and GetCapabilities |
| `GET /v1/maps/{id}@{version}/wms?…` | scoped | pinned dataset version; `410` once retired |
| `GET /v1/spatial/{id}/inspect?bbox=` | scoped | `spatial.inspect_region` |
| `GET /v1/spatial/{id}/nearby?x=&y=&radius=` | scoped | `spatial.find_nearby` |
| `GET /v1/worlds[/{id}[/snapshot|/events|/stream|/registration]]` | world-scoped | see NATIVE-WORLD-STREAMING.md |
| `POST /v1/admin/reload`, `POST /v1/admin/cache/purge` | admin | re-hash, regenerate, invalidate; SIGHUP also reloads |

## Contracts

- **Configuration** `finalverse.map-server-config/1`: strict. Unknown fields, non-absolute paths, mapfile-unsafe characters and non-allow-listed backend env vars are refused. Listening is loopback-only unless `allow_non_loopback`. Example: `finalverse/config/montreal.example.json`. FinalGIS generates deployments with `finalgis/scripts/map_server_config.py`.
- **Dataset version** = sha256 of the canonical JSON of {id, CRS, extent, layers with source sha256 and style}. A changed byte in any source, style or extent yields a new version.
- **Cache key** = sha256("finalverse.map-cache/1" ‖ dataset ‖ version ‖ backend binary sha256 ‖ canonical query). Entries are stored as `body` + `meta` with a body sha256. They are verified on every read and survive restarts. Entries for versions that are no longer live are removed on reload.
- **WMS canonicalisation**: keys are upper-cased; values are percent-decoded and checked for control characters; duplicates and unknown keys are refused (so `MAP=` injection is impossible); layers are checked against the catalog; `STYLES` must be default; WIDTH/HEIGHT are bounded; FORMAT is png/jpeg; BBOX is finite, ordered, must intersect the dataset footprint transformed with PROJ into the requested CRS, and may be at most 16× the footprint. WMS 1.3.0 northing-first axis order is honoured (the test proves 1.1.1 lon/lat and 1.3.0 lat/lon render byte-identical images).
- **Errors**: `{"error":{"code","message","request_id"}}` with stable codes. MapServer service exceptions are logged and returned as `502 backend_exception`, never relayed, because they can contain host paths.

## Verified behaviour

`finalverse/tests/integration.py` passes **73/73** with the world API enabled, and **63/63** without it against each of: the fork 8.7-dev, upstream rel-8-6-6, and an ASan/UBSan gateway build. The checks cover: health, auth (401/403/404 scoping), capabilities, GetMap in EPSG:2950/4326/3857 (png and jpeg), cache hit/canonical sharing, every refusal class, version pinning/retirement, spatial ops, metrics, malformed HTTP (400/431/405), 16 concurrent tiles, restart with recovered cache, byte-identical re-render after purge, source change → 409 → reload → new version, rate limiting (429), backend timeout (504, process reaped), saturation shedding (503), private token file, JSON logs, and tokens never logged.

Rendered output: `dev/omega-xvii-2-20261120/fvmap-integration.png` (512 px) and `demo/wms-montreal-1024.png`. Terrain uses `SCALE=AUTO` + bilinear resampling. The higher Old Montréal ground (NW) falls to the river (SE), consistent with the DTM statistics (12.9–29.5 m).

## Production status

Not production-certified: no TLS termination, no multi-host scaling or load test beyond the local measurements in PERFORMANCE.md, and no external security review. Development services bind to loopback.
