# Native live projection (Workstream B)

`libmutsea_replica` (MutSeaNative 0.4.0, `native/src/replica.cpp`, C ABI in
`native/include/mutsea/replica.h`) turns the verified Ω-XVII.2 decoder work into a
continuously maintained, **read-only** world projection fed by the authority's stream.

| Component | Implementation |
|---|---|
| Snapshot loader | SNAPSHOT_BEGIN/ENTITY/END, count + SHA-256 verified before adoption |
| Replication client | POSIX TCP, own thread, HELLO with durable cursor, ACK every 200 ms |
| Event validator | world/region/generation scope on every frame, Core `fvp_frame_decode`, frame sequence continuity |
| Projection state machine | staged EVENT/ENTITY, atomic apply on COMMIT, validation before any change |
| Revision tracker | revision + WorldLine (len, hash), native SHA-256 chain verification |
| Spatial entity index | radius query (nearest first), label lookup |
| Subscription manager | one subscription per handle (one region); several handles for several regions |
| Recovery manager | reconnect with 250 ms → 5 s exponential backoff, 7 s watchdog, crash-safe checkpoint (`FVRC` v1, SHA-256 sealed, fsync + rename) |
| Metrics | commits, duplicates, gaps, resyncs, reconnects, frames, bytes, latency p50/p95/max, checkpoint counters |

Invariants (tested): it never writes to the authority, and the API has no write call.
It rejects wrong-world frames and unsupported schemas, detects missing sequences
(gap → reconnect with cursor), applies duplicates idempotently, keeps entity
identities and the exact authority JSON (resident memory references included),
keeps WorldLine order, and resumes after a restart from its checkpoint without
re-snapshotting.

## Differential and fault tests (executed)

`native/tests/test_replica.cpp` (offline, crafted frames): snapshot, live commit,
duplicate, gap, wrong world, forged WorldLine hash, unchained record, recovery to
a correct commit, unsupported schema, truncated frame, header bit flip,
corrupted snapshot, foreign WELCOME, radius query. A rejected frame never
changes the projection. Release ctest 3/3.

`native/tests/live_replica.py` against the real Rust authority on a copy of the
preserved Montréal store (`dev/omega-xvii-3-20261121/live-replica-acceptance.json`):

| Scenario | Result |
|---|---|
| 1 differential, 60 live moves | native = Rust projection digest `27f3d647…`, revision 3044, identical WorldLine hash, 0 gaps; commit→native latency p50 0.23 ms, p95 0.37 ms |
| 2 connection dropped every 0.6 s while committing | 8 reconnects, all `resume`, identical digest, 1 snapshot total |
| 3 SIGKILL follower, 15 commits while dead, restart | checkpoint loaded, `resume`, 15 commits applied, identical digest |
| 4 authority drained and restarted under a running follower | reconnected by itself, identical digest, drain 1.34 s, restart 0.11 s |
| 5 bad token | refused 401, nothing projected |
| afterwards | `mutsea verify`: 3,146 records replayed from genesis |

Mismatch count across all scenarios: **0**.
