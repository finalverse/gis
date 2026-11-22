# FVP spatial domains

All domains share Core's canonical FVP 1.0 framing (`fvp.h`): a 48-byte header (major/minor, flags, domain, kind, schema major/minor, payload length, sequence, request id), tagged payload fields in strictly ascending order, CRITICAL/REPEATED flags, and limits of 1 MiB per frame, 1,024 fields and depth 4. No competing wire protocol is introduced.

| Logical domain | Number | Status |
|---|---|---|
| FVP.WORLD snapshot | 1 | existing (Core 0.2) |
| Gateway/profile | 2 | existing (Core 0.2) |
| **FVP.EVENT: MutSea WorldLine projection** | **3 (proposed)** | **implemented** in `mutsea_projection`; served by Map Server `/v1/worlds/{id}/stream` |
| FVP.MAP / FVP.GEO / FVP.SCENE / FVP.ASSET / FVP.AGENT / FVP.AI | — | evaluated below, not assigned |

## Domain 3, schema 1.0 (implemented)

| Kind | Header sequence | Fields |
|---|---|---|
| 1 EVENT | WorldLine seq | 1 BYTES world UUID · 2 BYTES region UUID · 3 U64 seq · 4 U64 journal revision · 5 BYTES prev hash (32) · 6 BYTES hash (32) · 7 TEXT entry (the exact hashed JSON bytes) |
| 2 HEAD | WorldLine length | 1 world · 2 region · 3 U64 length · 4 BYTES head hash · 5 U64 snapshot revision · 6 BYTES state digest |

A consumer can verify each event independently: `hash = SHA-256(u32le(19) ‖ "mutsea.worldline/v1" ‖ u64le(seq) ‖ prev ‖ entry)`. This is the same rule the Rust crate uses. A raw frame is still not an authenticated world statement (Core FVP rule). Authenticity comes from the transport (bearer token over loopback here) together with the chain.

## Evaluation of the other domains

- **FVP.MAP**: map tiles are images or vector tiles that existing standards (WMS/WMTS/OGC API) already serve, and the gateway serves WMS over HTTP. An FVP envelope would add nothing until the Viewer needs map content multiplexed on its FVP connection. Recommendation: not assigned yet.
- **FVP.GEO**: registration and pins are small documents. If carried, they should be domain-1 optional records referencing the MutSea pin digest, not a new domain.
- **FVP.SCENE / FVP.ASSET**: already covered by domain 2 asset requests/chunks for SpatialDB content.
- **FVP.AI / FVP.AGENT**: typed spatial operations (AI-SPATIAL-INTELLIGENCE.md) are request/response with JSON results today. They fit a future domain with kinds per operation once a non-HTTP consumer exists.

Registry action needed in Core: add domain 3 to `docs/native/FINALVERSE-FVP-SPECIFICATION.md`, and a Core-side decoder test using the golden frames in `dev/omega-xvii-2-20261120/demo/world-stream.fvp`.
