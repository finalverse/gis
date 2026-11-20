# Performance (measured)

Hardware: Apple M1, 16 GB, macOS 27.2.1, on battery/AC as found. Everything ran locally over loopback HTTP, with numbers taken from single runs of the integration suites (`dev/omega-xvii-2-20261120/*.json`). These are development measurements, not a load test.

## Map Server (Release gateway, fork backend 8.7-dev)

| Metric | Value |
|---|---|
| Startup to READY (hash 3 sources, write mapfiles, recover cache) | 0.10–0.69 s |
| GetMap 512×512, 3 layers, cache miss | 0.176 s |
| GetMap cache hit | 0.7 ms |
| 16 distinct 256² tiles, 16 client threads, 4 backend slots | 0.70 s total, p50 0.42 s |
| Cached requests, 16 client threads (Python urllib client-bound) | ~5,000 req/s |
| PNG size 512² (terrain+roofs+roads) | 125 KB |
| Restart → first request served from the recovered cache | HIT, byte-identical |

The rel-8-6-6 backend gives a similar picture (cold 0.159 s, 5,496 req/s cached). The ASan gateway: cold 0.160 s (rendering time is dominated by mapserv).

## MutSea native projection vs Rust oracle

| Store | Entities / WorldLine | Native open+verify | Native snapshot JSON | Rust oracle process (decode+verify) |
|---|---|---|---|---|
| Earth Montréal | 29 / 2,919 | 18.5 ms | 0.2 ms | 30.8 ms |
| Episode copy | 30 / 2,921 | 17.8 ms | 0.2 ms | 20.2 ms |
| Aetheria Skyreach | 68 / 1,396 | 9.7 ms | 0.3 ms | 12.1 ms |
| Fresh multiplayer store | 102 / 103 | 1.4 ms | 0.3 ms | 6.1 ms |

The Rust figures include process start, so this is not a like-for-like speed comparison. Snapshot JSON for Earth Montréal is 22 KB through the gateway.

## Spatial operations

`spatial.inspect_region` over the full 260 m × 260 m extent returns 17 roofs (30,916 m²), 41 road segments (1,833.8 m) and 28,561 DTM cells, in the same request time class as a WMS miss. Results are byte-identical across calls.

## Not measured (no evidence claimed)

Time to first visible Viewer frame, GPU frame time, scene update latency from commit to Viewer, CPU and memory profiles under sustained load, and recovery time after a network disconnect. These need the Viewer integration and a live replication feed (see NATIVE-WORLD-STREAMING.md).
