# MutSea Next: native foundation

## Implemented: `mutsea_projection` (MutSeaNative 0.3.0)

Branch `feat/omega-xvii-2-native-projection-20261120` in `~/Finalverse/mutsea` (`f5ccb32`, `b81f062`). It has a C17 header (`native/include/mutsea/projection.h`) and a C++23 implementation (`native/src/projection.cpp`). It is built and installed with the existing CMake package, linking Core's installed `finalverse_fvp` and SQLite.

| Directive component | How it is met |
|---|---|
| World registry read model | descriptor: world/region identity, bounds, tick rate, owner, default role, binding pin |
| Entity registry read model | every entity decoded from snapshot formats 1–3 (extensions: published origin, session, creative state) with per-entity digests `mutsea.entity/v1..v3` |
| Geographic registration read model | pinned `mutsea.geographic-binding/v1` (JSON) or `mutsea.world-placement/v1` (binary, decoded and version-checked) |
| World-state snapshot loader | newest snapshot; digest `mutsea.region-state/v1` recomputed and matched against the journal record; descriptor bytes matched against `meta.descriptor` |
| Event subscription client | WorldLine events after a `(seq, hash)` cursor, as JSON or FVP frames |
| Native world-state projection | the snapshot JSON / Map Server World Scene API |
| Revision tracking | journal revision vs snapshot revision (`lagging` flag), WorldLine length/hash |
| Restart-safe recovery | stateless apart from the client cursor; reopen-and-resume tested |
| Diagnostics | `last_error`, refresh counters, verified-record count, `open_mode` |

**Native WorldLine verification** is implemented: the hash chain is checked from genesis, then incrementally. A rewrite behind the verified head is detected. Core's FVP spec previously recorded native WorldLine verification as `REFERENCE_ONLY`.

### Safety properties

- `SQLITE_OPEN_READONLY`, `PRAGMA query_only`, and every prepared statement checked with `sqlite3_stmt_readonly`. No write path exists.
- A store fenced by the running writer yields `MS_PROJ_BUSY`. A store whose WAL still has content (writer running or crashed) is refused rather than read as immutable.
- Corruption classes are tested: tampered entry, gap, snapshot byte, record digest, foreign application id, future schema. Each yields `CORRUPT`, `NOT_A_STORE` or `SCHEMA`, never partial data.

## Differential verification against the authority

`native/projection-oracle` is a Rust binary built on the **accepted** `mutsea-world` codec and `mutsea-worldline::verify_chain`, reading through a read-only rusqlite connection (never the writer-locking runtime). `native/tests/projection_differential.py` compares field by field:

| Store (copy) | Entities | WorldLine | Mismatches |
|---|---|---|---|
| Earth Montréal (residents Elara, Terra, Lumi, Ignis, Kai, Auren) | 29 | 2,919 | 0 |
| Viewer episode copy of the same region | 30 | 2,921 | 0 |
| Aetheria Skyreach (world placement pin) | 68 | 1,396 | 0 |
| Fresh `mutsea multiplayer` store | 102 | 103 | 0 |

Compared fields: identity, revisions, tick, state and descriptor digests, role count, and for every entity its id, owner, creator, label, position and velocity **bit patterns**, revisions, digest and asset reference. Also compared: the binding pin, the WorldLine length and hash, and the store bytes before vs after. Resident memory lives in `civilization.sqlite` (Core), outside the region store. Its references are not part of this projection yet.

## Not done (deliberately)

- No second writer, no command path, no authority cutover.
- No decoding of journal `records` (TickRecord) for replay. State between snapshots is not reconstructed natively. The Rust stores keep a snapshot at the head, so `lagging` was false on every fixture.

## Authority-migration design (for later milestones)

1. **Live feed first.** Subscribe the native layer to the Rust `Replication` sink or the observer protocol (the writer fences file readers). Keep the `(seq, hash)` cursor contract shown here.
2. **Shadow replay.** Port the TickRecord decoder and the kernel transitions (the motion kernel is already matched over 519,000 entity-ticks in Ω-XIII.2), then replay records natively and compare state digests per revision with the Rust journal.
3. **Deterministic transitions + authorization.** Port policy (`mutsea-policy`), with WorldLine entries produced natively and checked byte for byte against Rust for the same inputs.
4. **Transactions and idempotency.** Command ids are already idempotency keys (`commands` table). Native commits must use one FULL-synchronous transaction per record, with the same digests.
5. **Controlled cutover.** Dual-run in shadow, then a writer-fence handover (stop Rust → native takes the EXCLUSIVE lock → verify head digests). Rollback means stopping native and restarting Rust on the same store, which works because the format is unchanged.
6. **Event persistence and snapshot recovery** stay format-compatible, so either engine can recover the other's store.
