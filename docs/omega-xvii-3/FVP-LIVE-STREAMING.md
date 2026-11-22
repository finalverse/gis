# FVP live world streaming (Workstream C)

Protocol `finalverse.world-replication/1` is **FVP 1.0, domain 3, schema 1.1**.
It extends the domain-3 schema 1.0 that Ω-XVII.2 implemented (kinds 1 EVENT and 2 HEAD
are unchanged) and adds no competing wire format. The Rust authority encodes frames
with a byte-compatible codec (`mutsea-network/src/fvp.rs`: 48-byte header, ascending
tags, CRITICAL/REPEATED, ≤1 MiB, ≤1,024 fields, depth ≤4). The native client decodes
them with **Core's own `fvp_frame_decode`**, so every live test is also a C↔Rust
interoperability test.

Transport: persistent TCP on loopback (the Viewer already runs local services this
way). No new dependency was introduced. Payload semantics are independent of the
transport, so TLS or WebSocket framing can carry the same frames later.

| Kind | Name (directive name) | Direction | Fields (tag type) |
|---|---|---|---|
| 1 | EVENT | S→C | 1 world · 2 region · 3 U64 seq · 4 U64 revision · 5 prev hash · 6 hash · 7 TEXT exact hashed entry |
| 2 | HEAD | S→C | unchanged from 1.0 |
| 3 | HELLO (WORLD.SUBSCRIBE / RESUME) | C→S | 1 TEXT protocol · 2 U64 major · 3 U64 minor · 4 TEXT token · 5 world · 6 region · 7 subscription id · 8 RECORD cursor {1 generation, 2 revision, 3 WL seq, 4 WL hash} |
| 4 | WELCOME | S→C | 1 negotiated minor · 2 subscription · 3 world · 4 region · 5 generation · 6 head revision · 7 WL length · 8 WL hash · 9 TEXT mode · 10 principal · 11 oldest ring revision |
| 5 | SNAPSHOT_BEGIN (WORLD.GET_SNAPSHOT) | S→C | 1 world · 2 region · 3 revision · 4 tick · 5 durable tick · 6 state digest · 7 generation · 8 WL length · 9 WL hash · 10 entity count |
| 6 | ENTITY | S→C | 1 id · 2 revision · 3 created revision · 4 label · 5 owner · 6–8 position · 9–12 rotation · 13–15 scale · 16–18 velocity · 19/20 asset authority/id · 21 context revision · 22 TEXT exact entity JSON |
| 7 | SNAPSHOT_END | S→C | 3 revision · 10 count · 11 SHA-256("finalverse.world-replication.snapshot/v1" ‖ Σ u32le(len) ‖ entity JSON) |
| 8 | COMMIT | S→C | 1 world · 2 region · 3 revision · 4 tick · 5 reason · 6 state digest · 7 first WL seq · 8 WL count · 9 WL length after · 10 WL hash after · 11 upsert count · 12 removed ids · 13 generation · 14 committed µs |
| 9 | ACK (WORLD.ACK) | C→S | 1 revision · 2 WL seq · 3 WL hash · 4 generation |
| 10 | RESYNC_REQUIRED (WORLD.RESYNC_REQUIRED) | S→C | 1 reason (generation, ahead, fork, slow_consumer) · 2 head |
| 11 | HEARTBEAT | S→C | 1 head revision · 2 WL length · 3 server ms |
| 12 | BYE | S→C | 1 reason (shutdown, region_stopped, unsubscribed) |
| 13 | ERROR | S→C | 1 code (400 malformed, 401, 403, 404 wrong world, 426 version, 503 overloaded) · 2 message |
| 14 | UNSUBSCRIBE (WORLD.UNSUBSCRIBE) | C→S | none |

A commit is the group `EVENT* ENTITY* COMMIT` and applies atomically on COMMIT. The
header sequence counts frames per connection, so a dropped frame is detected even
inside one commit. Version negotiation works like this: major must be 1, and the
minor is min(client, server). Client frames are bounded to 64 KiB before they are
read. Unknown non-critical fields are ignored and unknown critical fields are refused.

Not separately implemented: WORLD.DISCOVER (the token file and the session
gateway's `discover` give this), SCENE.* and GEO.* (Map Server routes and the
registration document cover them; see MAPSERVER-INTEGRATION.md).
