# Viewer and visual quality

## Changed in this milestone

- **Map rendering.** Terrain rasters now render with `PROCESSING "SCALE=AUTO"` and bilinear resampling. In Ω-XVII.1 the DTM rendered nearly black because 13–30 m values were mapped onto 0–255 without scaling. Polygons render with an outline, roads at 2 px, and the PNG output is RGBA with transparency available. This is actual application output: `dev/omega-xvii-2-20261120/fvmap-integration.png` (512²) and `demo/wms-montreal-1024.png` (1024², 282 KB), both produced by fvmapd → mapserv with the same bbox and size each run (re-rendering after a cache purge is byte-identical).
- **Data the Viewer can consume.** The World Scene API exposes entity transforms with exact bit patterns, labels, assets and published-origin pins. Six resident entities are visible in the Earth Montréal snapshot (Elara, Terra, Lumi, Ignis, Kai, Auren).

## Not changed (open)

The Viewer (`~/Finalverse/viewer`) and Storm (`~/Finalverse/storm`) were **not modified** in this milestone:

- Storm has active, separate rendering work (v0.3.1 convergence, IR stack). Changing its materials, lighting or shadows here would collide with that work.
- No foreground Viewer session was run, and no new Viewer screenshot is claimed. The Ω-XVII.1 foreground Viewer evidence still stands for the Ω-XVII.1 path.

Next steps, in order:

1. A Viewer data source for the World Scene API (snapshot + `(seq, hash)` events) behind its existing session abstraction.
2. Map Server WMS as a ground overlay texture: same bbox, EPSG:2950, presentation registration origin (300619.33, 5040809.31).
3. In Storm: terrain material from the DTM with the WMS overlay, roof materials, sun direction from the region's latitude and longitude, and a shadowed directional light, coordinated with the Storm v0.3.x owners.

Each of these needs its own foreground capture with fixed camera parameters before any claim is made.
