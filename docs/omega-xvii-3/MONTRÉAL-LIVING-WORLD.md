# Montréal Living World demonstration (executed 2026-11-21)

Reproduce:

```sh
cd ~/Finalverse/dev/omega-xvii-3-20261121
./living-world.sh start      # MutSea authority, Map Server, AI agent, Storm renderer
python3 montreal-demo.py     # Acts 1–11 with Viewer screenshots, writes montreal-demo-evidence.json
./living-world.sh stop
```

The store is `mtl/region.db`, a **copy** of the preserved Earth Montréal store
(source SHA-256 `cecf0d60…`, unchanged). Evidence: `montreal-demo-evidence.json`,
`shots/demo/`, `run/*.log`, `run/agent-records.jsonl`, and the Viewer log.

| Act | What happened (second run) | Evidence |
|---|---|---|
| 1 Infrastructure | `mutsea live` (Rust authority) at revision 3011, WorldLine 2944; fvmapd with the live world; agent; Storm renderer; then the Viewer with the native projection inside it | act1 |
| 2 Geography | dataset `montreal` version `3383a8f1…`, EPSG:2950, layers terrain/roofs/roads; registration `derived_model`, scope `presentation_only`, sha256 `3c2bb141…` | act2 |
| 3 Residents | Elara, Terra, Lumi, Ignis, Kai, Auren with entity ids and revisions from a fresh authoritative snapshot | act3 |
| 4 Compose | Viewer LIVE at revision 3011, mode `resume` (checkpoint); Storm frame from source revision 3011; badge "Presentation-only registration · not surveyed" | `act04-compose.png` |
| 5 AI query | typed in the Viewer's Ask bar (scripted): gemma4:e4b plan of 2 steps in 13.9 s; 10 buildings within 100 m of Elara "by presentation proximity (registration not surveyed)" | `act05-ai-query.png`, agent records |
| 6 Authorized action | Viewer's move controls (scripted): Elara +5 E, +5 N; Terra −5 E; each committed by MutSea under the agent mandate (receipt ~52–59 ms) | `act07*.png` |
| 7 Live propagation | commits reached the Viewer through the stream (pill latency 0.42–0.77 ms), WorldLine feed #2945–#2947, residents "moved N s ago", Storm re-rendered Elara at (335, 335) | `act07b-live-moves-settled.png` |
| 8 Disconnect | Viewer process stopped; 6 authorized moves committed meanwhile (all applied) | act8 |
| 9 Reconnect | Viewer restarted from its checkpoint, mode `resume`; Viewer revision 3020 = authority revision 3020; the six records appear in the feed | `act09-reconnected.png` |
| 10 Restart | authority drained (shutdown record), Viewer showed RECONNECTING and "Connection lost · showing last confirmed revision 3021"; authority restarted, a move committed, Viewer back at 3022 = authority | `act10a-authority-down.png`, `act10b-recovered.png` |
| 11 Visual inspection | select and focus Auren (camera on her body), then overview | `act11a-focus-auren.png`, `act11b-overview.png` |
| 12 Evidence | this document, ACCEPTANCE.md, `OMEGA-XVII-3-DELIVERY.json` | — |

Note: the Viewer's p95 latency after Act 9 includes the six commits made while the
Viewer was stopped. They are delivered at reconnect, so their commit→display time
is the disconnection time, not stream latency.
