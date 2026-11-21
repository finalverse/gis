# Map Server integration (Workstream D)

MapServer fork branch `feat/omega-xvii-3-map-live-world-20261121` (commit 6b2e0f421).

A world entry may now name `"live": "<mutsea live-tokens.json>"` instead of
`"store"` (exactly one is required). The gateway then subscribes to the authority's
replication stream through `libmutsea_replica` (read-only subscriber, checkpoint in
`state_dir/world-<id>.replica`). The offline projection path is unchanged.

| Route | Live behaviour |
|---|---|
| `GET /v1/worlds/{id}` | source, protocol, world, region, **generation**, state, mode, `current`, revision, head, `lagging`, verified WorldLine head, latency |
| `GET /v1/worlds/{id}/snapshot` | exact authoritative entity JSON at a stated revision; **503 world_not_current** while reconnecting or syncing; 503 world_moving if the revision changed during assembly |
| `GET /v1/worlds/{id}/events` | live WorldLine window with cursor/hash check; 409 resync_required outside the window |
| `GET /v1/worlds/{id}/stream` | 409 use_replication_stream (FVP comes from the authority directly) |
| `GET /v1/worlds/{id}/nearby?x&y&radius&limit` | **new**: spatially filtered authoritative entities (region-local metres, nearest first, deterministic) |
| `GET /v1/worlds/{id}/registration` | presentation registration document + hash; no authoritative binding for this region |

Ownership stays split. Map Server owns geography, catalog and spatial queries, and
serves world views read-only. MutSea owns entities, transforms, permissions,
actions and WorldLine. No route can commit.

**Cache correctness.** Every world response names the world, generation and revision
it describes. World views are never put into the WMS cache. Geographic cache keys
already include the dataset version (Ω-XVII.2). A projection that is not current
refuses snapshots and spatial views instead of serving stale state as current.

Verified live (`fvmap-live/fvmapd`, config `dev/omega-xvii-3-20261121/map/config.json`):
head reported `state live, current true, revision 2997`; `nearby(323, 326, 10 m)`
returned Elara at 5.02 m. The Ω-XVII.2 regression suite is in ACCEPTANCE.md.
