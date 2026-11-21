# Performance (measured, Apple M1 16 GB, macOS 27.2, release builds)

The machine was heavily loaded during several runs: a full Viewer rebuild ran at
the same time with a load average of about 33, and an unrelated `civilization-gw3`
process was active. Numbers are what was observed, not best-case figures.

| Metric | Value | Source |
|---|---|---|
| Authority recovery of the Montréal store (29 entities, ~3,000 records) | 69–178 ms | `mutsea live` startup line |
| Durable ack of one authorized move (single client) | p50 33.9 ms, p95 50.2 ms | `live-bench --clients 1` (200 moves) |
| Durable commands/s, 8 concurrent clients | 207 /s (p50 ack 33 ms, p95 72 ms); 139 /s on a second run under heavier load | `accept1/bench-8.json`, `bench-8b.json` |
| Commit → native projection latency, light load | p50 0.23 ms, p95 0.37 ms, max 1.18 ms | live_replica scenario 1 |
| Commit → native projection latency, 800 moves in ~6 s | p50 1.86 ms, p95 15.8 ms, max 86 ms; 800/800 WorldLine records verified | `accept1/bench-native.json` |
| Initial snapshot (29 entities) to LIVE | < 50 ms (within the first status tick) | native follower |
| Reconnect after dropped connection | resumed with 0 gaps; 8 reconnects in 14 s of 0.6 s drops | scenario 2 |
| Authority drain + restart | 1.34 s drain, 0.11 s to serving; follower resumed itself | scenario 4 |
| Storm frame (registered Montréal, OGRE Metal, 1280×720) | 64,215 triangles, 144 objects; captured frames ≈4/s (Ω-XV capture bridge) | `run/frames/frame.json` |
| AI typed plan (gemma4:e4b) | 18.5–19.3 s per plan | agent records |
| Map Server live head / nearby | served from memory (projection already current) | fvmapd log |

Not measured: GPU timestamps and VRAM peak (the frozen renderer exposes no GPU
timers), Viewer frame time under live updates (see VIEWER-STORM-INTEGRATION.md for
what was captured), and CPU/memory under sustained multi-hour load.
