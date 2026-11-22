# Native world streaming

## Content classes

| Class | Source of truth | Delivered by | Status |
|---|---|---|---|
| Static geographic content (terrain, roofs, roads) | FinalGIS datasets, versioned by digest | Map Server WMS + spatial API | implemented |
| Versioned scene assets (GLB/FWD) | SpatialDB publication | Ω-XVII.1 Forge/SpatialDB path; the catalog carries the publication reference | reused, unchanged |
| Dynamic authoritative entities | MutSea region store (Rust writer) | MutSea native projection → Map Server World Scene API | implemented, read-only |
| Viewer-local presentation state | Viewer | n/a | unchanged |

## World Scene API (implemented)

| Route | Returns |
|---|---|
| `GET /v1/worlds` | worlds visible to the principal, each with its head |
| `GET /v1/worlds/{id}` | head: world/region, snapshot revision, journal revision, `lagging`, tick, state and descriptor digests, entity/role counts, WorldLine `{length, hash, verified}`, `open_mode` |
| `GET /v1/worlds/{id}/snapshot` | full decoded state: descriptor, roles, every entity (transform, velocity, exact IEEE bit patterns, asset reference, digests, published origin, session, creative state) |
| `GET /v1/worlds/{id}/events?after=S&after_hash=H&limit=N` | WorldLine entries after cursor `(S, H)`, each with `seq/revision/prev_hash/hash/entry`, plus `complete` |
| `GET /v1/worlds/{id}/stream?after=…` | the same batch as FVP 1.0 frames (`application/x-finalverse-fvp`) |
| `GET /v1/worlds/{id}/registration` | the authoritative MutSea pin (decoded) and the presentation registration document |

Streaming semantics:

- **Sequence numbers**: the WorldLine `seq` is 1-based and contiguous.
- **Gap detection**: a cursor ahead of the head, or a cursor hash that is not on this chain, returns `409 resync_required`. The client then takes a snapshot and restarts from its head.
- **Idempotent application**: an event is identified by `(seq, hash)`. Re-applying the same `seq` with the same hash is a no-op.
- **Reconnect and restart**: the cursor is `(seq, hash)` and needs no server session. The live-follow test persists it, reopens and resumes with zero missed events.
- **Bounded memory**: the projection keeps only the decoded snapshot and the verified chain head. Events are read in bounded batches (limit ≤ 1024) and are never cached.
- **Backpressure**: the client pulls, so the server never pushes faster than it is asked. The gateway's rate limiter and worker queue bound load.

### FVP mapping (proposed domain 3, schema 1.0)

This reuses Core's `fvp_frame_encode` (48-byte header, tagged fields, ascending tags). There is no new wire format.

- kind 2 HEAD, `sequence` = WorldLine length: 1 world UUID, 2 region UUID, 3 length U64, 4 head hash, 5 snapshot revision U64, 6 state digest.
- kind 1 EVENT, `sequence` = seq: 1 world, 2 region, 3 seq, 4 revision, 5 prev hash, 6 hash, 7 entry TEXT (the exact JSON bytes that were hashed).

The frames decode with Core's `fvp_frame_decode` in `test_projection.cpp`. Domain 3 still has to be added to Core's FVP registry (`docs/native/FINALVERSE-FVP-SPECIFICATION.md`). That is listed in MIGRATION-ROADMAP.md.

## Key finding: the authority fences live readers

The accepted Rust writer opens stores with `locking_mode=EXCLUSIVE` (`mutsea-persistence`, line 171). While it runs, **no other process can read the store**. `live_follow.py` runs the real `mutsea multiplayer` reference (region service, TCP gateway, authenticated clients). The native projection received **MS_PROJ_BUSY 29 times** while the writer was alive, so no torn or partial state was ever observed. After exit it caught up **103/103** events, contiguous, with its head equal to an independent reopen and `mutsea verify` passing (104 records replayed).

So a live, concurrent stream cannot come from reading the authoritative file. It has to come from the authority's own replication feed: the Rust runtime already has `Replication { max_hz, sink }` and authenticated network observers. The native projection is correct for checkpoints, offline replicas and recovery verification, and its event/cursor contract is the one a replication-fed stream should keep. This is the first item of MUTSEA-NEXT-ARCHITECTURE.md.

## Not done

- No Viewer code was changed in this milestone. The Viewer still uses its Ω-XVII.1 path (Core native gateway snapshot over a Unix socket plus the static admission).
- Interest management and region subscription across multiple regions are specified only. The current API serves one configured region per world entry.
