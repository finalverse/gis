# MutSea live replication (Ω-XVII.3, Workstream A)

Code: `finalverse/mutsea` branch `feat/omega-xvii-3-live-replication-20261121`
(commits fd6a33d, bd56e45, 7b7e865, 925974f). Local only, nothing pushed.

## Commit coupling: the WorldLine is the outbox

MutSea already commits a tick record, its command index and its hash-chained
WorldLine entries in **one SQLite transaction** (`synchronous=FULL`, `fullfsync`).
So no new outbox table or schema migration is needed, and the preserved stores
keep schema 2.

`RegionHost::run` captures the WorldLine head before `CommitLog::append`. Only
after `append` returns success does it build a `CommitEvent`:

| Field | Meaning |
|---|---|
| world, region | scope of the event |
| revision, tick, reason | the journal record (`commands`, `checkpoint`, `shutdown`) |
| state_digest | the record's digest of the full state |
| worldline | the record's WorldLine records, chained (`chain_after`) exactly as stored |
| worldline_head | chain head after the record |
| upserts / removes | entities the record changed, as of `revision` (commands' effects plus simulated motion made durable by that record) |
| committed_unix_us | wall clock after the durable append (latency measurement only) |

A failed append fences the region and produces no event. **An event is never
visible before its transaction is durable.** There is still exactly one writer:
the publisher only reads the host's own state and the writer's own connection.

## Publisher and ring

`RegionService::spawn_live` hands the events to a `CommitSink` on the region
thread in revision order, including the drain and shutdown records written by
`shutdown()`. `CommitRing` (mutsea-network) is a bounded window (`--ring`, 65,536
by default) plus a `watch` channel holding the head revision. Subscribers read the
ring at their own pace, so nothing is queued per subscriber beyond the socket.
Memory is bounded by the ring, whatever the number or speed of consumers.

Catch-up beyond the ring reads WorldLine records through the **writer's own
connection** (`CommitLog::worldline_after`, a new read-only method served on the
region thread). The authoritative store is never opened a second time, and no
lock is bypassed.

## Durable cursor contract

`(generation, revision, worldline_seq, worldline_hash)`

* **generation**: the store's descriptor digest. It stays the same across restarts of
  the same store and differs for any other store. It replaces "epoch" for durable resume.
* **revision**: the journal revision. It is contiguous and totally ordered **within one region store**.
* **worldline_seq/hash**: position on the hash chain. Contiguous and verifiable.
* **schema version**: carried by every FVP frame header (domain 3, schema 1.1).

Ordering scope: one region store. Nothing orders events of different regions or
worlds, and an event id alone is never treated as a global order.

## Delivery semantics

At least once, with idempotent application. A commit applies only on top of
`revision - 1`. Lower revisions count as duplicates and are ignored. A higher
revision is a gap: the client drops the connection and resubscribes with its
cursor. A WorldLine record applies only when it chains to the verified head.

Server decision on HELLO with a cursor:

| Condition | Mode |
|---|---|
| no cursor | `snapshot` |
| other generation / cursor ahead of head / hash not on this chain | `resync`: RESYNC_REQUIRED(reason) then snapshot |
| cursor at head, or next revision still in the ring | `resume`: missed commits from the ring |
| cursor on the chain but older than the ring (e.g. after authority restart) | `catchup`: **every** missed WorldLine record from the store, then a snapshot |

No event is skipped silently. Either the commits themselves arrive, or every
missed WorldLine record plus a snapshot arrives, or the client is told
RESYNC_REQUIRED.

## Backpressure, slow consumers, shutdown

Writes have a deadline (`write_timeout`, 5 s). A subscriber that cannot drain
within it is disconnected, and its cursor stays valid. A subscriber that falls out
of the ring window gets RESYNC_REQUIRED(`slow_consumer`) plus a snapshot. A graceful
stop drains, writes the shutdown record, publishes it, then sends BYE(`region_stopped`).

## Authentication and authorization

Every subscription is a bearer token (`TrustedLocalAuthenticator`; `mutsea live`
keeps stable tokens in a 0600 file). A subscription names exactly one world and
region and is refused with 404 otherwise, so cross-world leakage is impossible by
construction. Mutations never travel on this stream. Moves go through the existing
command gateway and MutSea policy (`agent:<owner>` tokens carry only the Modify scope).

## Tests (all executed)

* `cargo test --workspace`: all pass, clippy clean. New `tests/live.rs` has 6 tests:
  snapshot → live → disconnect/resume → authority restart/catch-up; cursor expiry
  with every WorldLine record verified; forked/foreign cursor resync; refusals
  (401, 404, 426, garbage, oversized frame); slow consumer disconnect while a
  healthy one converges; graceful BYE after the shutdown commit.
* Real Montréal store copy (`mutsea live`): Elara moved by her agent, durable ack
  41 ms, delivered as revision 2985.
