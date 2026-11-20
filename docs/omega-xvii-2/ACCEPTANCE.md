# Ω-XVII.2 acceptance

Status: **partial**. The gates below are marked PASS only where executable evidence exists. Everything is local and unpushed.

## Gates

| Gate | Status | Evidence |
|---|---|---|
| Preserved FinalGIS branding | PASS | Product layer byte-identical on both branches; branding sources untouched; FinalGIS.app 0.3 unchanged |
| Verified upstream source/version information | PASS | FINALGIS-UPSTREAM.md (no 4.4.0; 4.2.3 `b041a18904a`; LTR 3.44.15; #67981 open) |
| Upstream 4.2.3 source build | **OPEN** | Product-layer branch exists. The headless source build is blocked by the Homebrew Qt mismatch, which waits on owner approval. |
| Working MapServer integration | PASS | 63/63 on fork 8.7-dev, rel-8-6-6 and ASan; 73/73 with the world API |
| Stable geographic publication | PASS | Dataset versions by digest, pinned/retired versions, byte-identical re-render, restart recovery; publication reference carried in the catalog |
| Explicit spatial registration semantics | PASS | Validator reproduces the anchor to 3.7 µm and classifies it presentation_only; refusals tested |
| Surveyed registration | **OPEN** | No control points or epoch exist, and none were invented |
| Working native world streaming | **PARTIAL** | Snapshot + `(seq,hash)` events + FVP frames + gap/fork detection + resume: PASS. Live concurrent stream from the authority: blocked by design (EXCLUSIVE writer fence); needs the replication feed. |
| Native MutSea read-only projection | PASS | 0 mismatches vs the Rust oracle on 4 stores; ASan/UBSan pass; tamper classes detected |
| Real Viewer/Storm rendering of new path | **OPEN** | Viewer and Storm unchanged this milestone. Real MapServer output only (see VIEWER-VISUAL-QUALITY.md). |
| Preserved world authority | PASS | Read-only by construction; store digests unchanged; `mutsea verify` passes after the follow test |
| Restart recovery | PASS | Gateway cache and versions; projection cursor resume |
| Passing relevant tests | PASS | Lists below |
| Reproducible demonstration evidence | PARTIAL | Steps below |

## Test commands and results

| Suite | Command (build dirs under `dev/omega-xvii-2-20261120`) | Result |
|---|---|---|
| FinalGIS native | `ctest --test-dir build` | 6/6 (workflows, C17 ABI, workflow v2, registration, spatial policy, SpatialDB bridge) |
| Gateway units | `fvmap-build/fvmap_unit_tests`, `fvmap-asan/fvmap_unit_tests` | pass / pass (ASan+UBSan) |
| Gateway integration | `python3 MapServer/finalverse/tests/integration.py --fvmapd … --mapserv … --source … --env-prefix … [--world-store … --world-registration …]` | 63/63 ×3 backends/builds; 73/73 world-enabled |
| Gateway fuzz | `fvmap-fuzz/fvmap_fuzz_wms -max_total_time=180 fuzz-corpus` | 4,598,362 runs, 0 findings |
| MutSea native | `ctest --test-dir mutsea-build`, `mutsea-asan` | 2/2, 2/2 (projection + existing motion recovery) |
| MutSea differential | `python3 mutsea/native/tests/projection_differential.py …` | 4/4 stores, 0 mismatches |
| MutSea live follow | `python3 mutsea/native/tests/live_follow.py …` | pass (29 BUSY while writer alive; 103/103 events; resume 0 missed) |

## Reference demonstration (directive §12.2)

| # | Step | Status |
|---|---|---|
| 1 | FinalGIS launches with branding | carried from Ω-XVII.1 (not re-run in foreground) |
| 2 | Verified dataset loads | PASS (catalog digests) |
| 3–4 | Local model typed plan, reviewed | PASS: gemma4:e4b typed spatial plans with policy; Ω-XVII.1 Qwen GIS plan path unchanged |
| 5–6 | Deterministic tools, validated output | PASS (inspect/nearby/registration) |
| 7–8 | Scene package, SpatialDB publication | carried from Ω-XVII.1 (publication reference served in catalog) |
| 9 | Map Server serves a real map request | PASS |
| 10–12 | Viewer loads, Storm renders, user navigates | OPEN for the new path |
| 13 | MutSea supplies an existing resident | PASS (snapshot through the World Scene API: Elara, Terra, Lumi, Ignis, Kai, Auren) |
| 14 | Resident shown without fabricated registration | PASS at the data level (registration served as presentation_only; authoritative pin "none") |
| 15–16 | Authorized action updates state; WorldLine records it | PASS for a real Rust-authority run (`mutsea multiplayer`, 103 WorldLine records) observed natively. Not performed on the preserved Montréal world, which was not modified. |
| 17–18 | Services restart; same state and publication recovered | PASS (gateway restart + cache; projection reopen/resume) |

## Commits

| Repository | Branch | Commits |
|---|---|---|
| FinalGIS | `feat/omega-xvii-2-mapserver-20261120` | `00c45af2116` (+ this docs commit) |
| FinalGIS | `feat/finalgis-upstream-4.2.3-20261120` | `cf8790f5519` |
| MapServer fork | `feat/finalverse-map-server-20261120` | `f91749013dd` (+ README commit) |
| MutSea | `feat/omega-xvii-2-native-projection-20261120` | `f5ccb32`, `b81f062` |

Machine-readable receipt: `dev/omega-xvii-2-20261120/OMEGA-XVII-2-DELIVERY.json`.
