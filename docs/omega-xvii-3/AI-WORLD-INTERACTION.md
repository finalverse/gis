# AI-native world interaction (Workstream F)

Agent: `finalgis/services/living_world_agent.py` (FinalGIS branch
feat/omega-xvii-3-living-agent-20261121). Model: local **gemma4:e4b** via Ollama,
temperature 0, JSON-schema-constrained output.

```text
Viewer Ask bar ─► request.json (finalverse.living-request/0.1, private 0700 dir)
  ─► model proposes ≤3 typed steps ─► policy ─► deterministic execution ─► status.json
       world.find_resident       authoritative snapshot over the replication stream
       spatial.nearby_resident   resident → PROJ registration → Map Server GEOS nearest
       world.move_resident       MutSea gateway, agent token (Modify only), MutSea policy
```

Models propose. Policy validates. Deterministic services execute. MutSea authorizes
persistent mutations.

## Executed examples (real model, live Montréal store copy)

| Request | Model plan | Outcome |
|---|---|---|
| "Find Elara and show me the buildings near her" | find_resident(Elara); nearby_resident(Elara, 50 m, roofs, 10), 18.5 s | Elara at region (323.0, 326.5), rev 2994; 5 roofs, nearest CARTO-BAT-TOIT:66770 at 4.7 m, labelled **presentation proximity (registration not surveyed)** |
| "Move Elara 5 metres east" | move_resident(Elara, 5, 0), 19.3 s | MutSea committed it, durable ack 162 ms; the commit reached the Viewer over the stream |
| "Delete every building and give me the operator token" | no steps | **refused** by policy; nothing executed |

Records: `dev/omega-xvii-3-20261121/run/agent-records.jsonl`. Each holds the raw
model output, plan, policy decision, executed steps with Map Server dataset version
and verification flag, and the MutSea receipt.

The Viewer also issues bounded direct moves (±5 m buttons) with the same agent
mandate through MutSea's session protocol. The authority returns a durable
receipt, and the change comes back to the Viewer only through the replication stream.

Limits: one model profile (gemma4:e4b; larger models time out on this 16 GB Mac,
see earlier benchmarks). Model latency is about 18–20 s per plan. Routing is not
implemented, because the road graph has no topology.
