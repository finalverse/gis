# Security

| Control | Implementation | Tested by |
|---|---|---|
| Authentication | Bearer tokens. The token file holds only SHA-256 digests (`finalverse.map-server-tokens/1`) and must be mode 0600. Comparison is constant-time across all entries. | integration: 401 unknown/absent token; check-config refuses a 0644 file |
| Authorization | Roles `reader`/`admin`. Per-principal dataset and world scopes. Unknown or forbidden resources both return 404 (no existence oracle). Metrics and admin routes are admin-only. | 403 metrics/reload, 404 stranger dataset/world |
| World isolation | Per-world scopes. The projection is read-only (SQLITE_OPEN_READONLY, query_only, read-only statement check). The authority's EXCLUSIVE fence is respected. | projection tests; store bytes hashed before and after |
| Dataset access control | Catalog filtered per principal. WMS, spatial and pinned-version routes check scope before work. | integration |
| Resource quotas | Token-bucket rate per principal (429 + Retry-After). Worker pool with bounded accept queue (503 when full). Backend slot semaphore with queue timeout (503). WIDTH/HEIGHT/bbox-ratio caps. Raster window ≤ 4M cells, feature scan ≤ 100k, nearby radius ≤ 2 km, events limit ≤ 1024. | rate-limit, saturation, size refusals |
| Input validation | Strict config and WMS schemas. Percent-decoded values checked for control characters. Duplicate and unknown parameters refused. Literal path matching only (no `..`, `%`, `\` or `//`). Header limit → 431. | unit tests, integration, libFuzzer |
| Path traversal / mapfile injection | Mapfiles are generated from validated config only. MapServer runs with `MS_MAP_NO_PATH=1` and alias-only `map=`. A client `MAP` parameter is refused. Paths with quotes or control characters are refused at config load. | `refuse map injection` |
| Service timeouts / cancellation | Backend killed with SIGKILL at its deadline and reaped. Socket read/write timeouts. Graceful SIGTERM drains workers. | 504 test + reaped-process check |
| Backend isolation | `posix_spawn` with `POSIX_SPAWN_CLOEXEC_DEFAULT`, a fresh environment (allow-listed vars only), `PROJ_NETWORK=OFF`, stdin=/dev/null, output cap. The backend binary is identified by sha256, which can be pinned in config. | startup identity check |
| Error hygiene | Stable error codes. MapServer exceptions (which may contain host paths) are logged, never relayed. GetCapabilities contains no host paths. | integration (`/Users/` absent) |
| Structured logging | JSON lines: request id, principal, route, status, bytes, µs, cache. Tokens are never logged. | integration scans every log line for token values |
| Secrets | No secret in any repository. Tokens are generated per deployment into private 0600 files outside the repo (`map_server_config.py`). | review |
| Network exposure | Loopback by default. A non-loopback bind requires an explicit `allow_non_loopback`. | config unit test |

Fuzzing: `fvmap_fuzz_wms` (libFuzzer + ASan + UBSan, LLVM 22) ran **4,598,362 executions in 181 s** with no findings after the two fixes below. Seed corpus: `dev/omega-xvii-2-20261120/fuzz-corpus`.

Defects found by the sanitizers and fuzzer, then fixed:

1. Heap use-after-free in cache eviction: a key reference into the LRU list outlived its node. Fixed by copying the key.
2. Heap read overflow: `boost::urls::parse_query` read past a non-NUL-terminated `string_view`. Fixed by parsing an owned string.

Not yet done: TLS (terminate in front of fvmapd before any non-loopback exposure), external penetration test, token rotation tooling beyond reload, and audit-log retention.
