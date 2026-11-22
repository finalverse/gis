# Viewer and Storm integration (Workstream E)

Viewer branch `feat/omega-xvii-3-living-viewer-20261121` (commit af8c47613a, on the
Ω-XV build host `dev/worktrees/viewer-ai-world`). This is the maintained C++ Viewer,
not a standalone renderer test.

## Composition

```text
MutSea authority ─FVP domain 3─► libmutsea_replica (inside the Viewer process)
   residents, entities, WorldLine, cursor, state ──► Living World console (new floater)
   authoritative region position ─► libworld_convergence (presentation-only registration)
                                 ─► scene-update.json (finalverse.scene-update/0.1)
Storm/Metal child (Ω-XV finalverse-living-render, registered Montréal FWD, 64,215 tri)
   ◄─ camera.json (presentation control)            ─► frame.ppm/json (pixel-hash verified)
Console viewport ◄── Storm frame, full-bleed, cropped not stretched
Map Server ─► geography (WMS/catalog), spatial queries for the AI agent, live world API
```

| Required behaviour | Implementation |
|---|---|
| World selection | the console binds to the world/region named by the token file (one region per console). The Ω-XV multi-world floater is unchanged and still available |
| Scene loading | registered Montréal FWD rendered by Storm; definition pin checked on every frame |
| Resident discovery | live from the replica: entities labelled "AI resident", with asset identity from the exact authority JSON |
| Dynamic transform updates | each new revision writes a full resident snapshot to Storm (cursor = revision, epoch = generation); Storm smooths toward committed positions |
| Object selection / inspection | resident cards (click), inspector with authoritative region coordinates, displayed E,N,U (presentation), revision, entity and body asset |
| Camera navigation | wheel zoom, arrows yaw/pitch, F focus, O orbit, Home overview, "Follow NAME"; focus targets the resident's body in Storm |
| Loading indicator | spinner and "Synchronizing with the authority…" until the first snapshot |
| Disconnect indication | status pill (LIVE / SYNCING / RECONNECTING / REFUSED) and a centre banner: "Connection lost · showing last confirmed revision N"; the viewport is dimmed |
| Reconnection / resync | automatic (replica backoff + checkpoint); "Resynchronized from a fresh authoritative snapshot" when the server forced it |
| Registration status | permanent badge "Presentation-only registration · not surveyed" with `derived_model · scope presentation_only · EPSG:2950 → region-local · rev 1` |
| Authorized actions | ±5 m moves sent over MutSea's session protocol with the resident owner's agent token; the receipt is shown, and the result arrives only through the stream |
| AI | Ask bar + suggestion chips → agent → typed-plan result card with policy line; the camera focuses the answer's resident |

## UI/UX redesign (owner request, 2026-11-21)

Before: `dev/omega-xvii-3-20261121/shots/before-viewer-xv.png` (Ω-XV floater: grey
button rows, empty viewport box, form-like layout). After: `shots/demo/*.png`. The
new console is a full-bleed 3D view under glass panels with a consistent design
system (tokens for ink, glass, accent, live, warning), large typography,
per-resident colour identity, movement pulses on cards and the live map, a status
pill with a live heartbeat, a WorldLine ticker that highlights new records, and an
AI command bar with contextual chips. All drawing is native Viewer GL (no web view
and no new UI dependency).

## Storm visual quality

The frozen Ω-XV renderer was reused, not rewritten (shadows/PBR/sky as in Ω-XV).
Ω-XVII.3 improves the camera framing (initial 420 m overview at −0.55 pitch, 26 m
focus at −0.38), keeps the frame dimmed when not live, and adds legibility
vignettes. No new renderer features (AA/IBL/HDR) were claimed.

## Evidence (executed)

`dev/omega-xvii-3-20261121/montreal-demo.py` → `montreal-demo-evidence.json` and
`shots/demo/act04…act11*.png`. The Viewer log line `FinalverseLiving … live
revision=R … scene_revision=R frame=F frame_source_revision=R` shows the Storm frame
rendered from the same revision.

Limits: the captured-frame bridge (~4 frames/s) and CPU readback remain from Ω-XV.
Selecting by clicking a body in the 3D view (ray picking) is not implemented;
selection is through the rail. Window placement starts at the floater view's origin,
not the window's left edge. The PROJ dylib is resolved from the recorded GIS
environment through an rpath (local build only, not a distributable bundle).
