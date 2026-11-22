# Ω-XVII.3 baseline recovery (P0)

Verified on 2026-11-21 (Mac QMBP13-3, Apple M1, 16 GB, macOS 27.2): 23 GB free at
the start and about 20 GB during the work.

| Repository | HEAD at start | State |
|---|---|---|
| mutsea | `b81f062` feat/omega-xvii-2-native-projection-20261120 | clean, matches the Ω-XVII.2 receipt |
| MapServer fork | `5aab5312f` feat/finalverse-map-server-20261120 | clean, matches the receipt |
| FinalGIS | `cd4166003b8` (finalgis-ai worktree) / `cf8790f5519` (4.2.3 branch) | clean |
| storm | `6a4f992` | clean, pushed earlier |
| viewer host | `75ff4926a3` feat/omega-xv-viewer-host-20261119 (build tree present) | clean |

Ω-XVII.2 receipt: `dev/omega-xvii-2-20261120/OMEGA-XVII-2-DELIVERY.json`.
Re-verified here: the current Rust MutSea recovers a copy of the preserved
Montréal store (29 entities, 2,919 commands, WorldLine verified, source SHA-256
`cecf0d60…` unchanged). The fvmapd regression is recorded in MAPSERVER-INTEGRATION.md.

**Qt.** The owner upgraded every Homebrew Qt module to 6.12 at 09:48 on 2026-11-21.
qtbase, qtdeclarative, qttools and the rest are linked at 6.12 (frameworks report
6.12; `qmake -query QT_VERSION` = 6.12.0). The 6.11.1 kegs are still installed and
unlinked. No package change was made in Ω-XVII.3.

New Ω-XVII.3 work lives on new local branches:

| Repository | Branch | Worktree |
|---|---|---|
| mutsea | feat/omega-xvii-3-live-replication-20261121 | dev/worktrees/mutsea-omega-xvii-3-20261121 |
| MapServer | feat/omega-xvii-3-map-live-world-20261121 | dev/worktrees/mapserver-omega-xvii-3-20261121 |
| FinalGIS | feat/omega-xvii-3-living-agent-20261121 | dev/worktrees/finalgis-ai-20261120 |
| viewer | feat/omega-xvii-3-living-viewer-20261121 | dev/worktrees/viewer-ai-world |

Nothing was pushed, merged, published or deployed. Preserved stores were only
ever copied (`dev/omega-xvii-3-20261121/{mtl,accept1,fvmap-regress}`).
