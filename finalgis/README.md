# FinalGIS 0.3 geographic workflows

Geographic Intelligence for Living Worlds. A separately built C++ worker and supported QGIS product extension; upstream functionality/history remain intact. See [architecture](docs/FINALGIS-ARCHITECTURE.md), [runtime/source lock](foundation.lock.json), [acceptance](docs/FINALGIS-ACCEPTANCE.md) and [license inventory](docs/FINALGIS-LICENSING.md).

Build the native worker with Qt6.8+ and GDAL3.10+ development packages (the tested versions are in the lock):

```sh
cmake -S finalgis -B /tmp/finalgis-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/path/to/qt;/path/to/gdal-prefix" -DFINALGIS_PROJ_DATA_DIR=/path/to/matching/proj/data
cmake --build /tmp/finalgis-build -j4
ctest --test-dir /tmp/finalgis-build --output-on-failure
/tmp/finalgis-build/finalgis-worker inspect --source finalgis/fixtures/montreal
/tmp/finalgis-build/finalgis-worker plan --request 'Analyze Montréal roads and roofs' --provider mock > /tmp/finalgis-plan.json
/tmp/finalgis-build/finalgis-worker run --source finalgis/fixtures/montreal --plan /tmp/finalgis-plan.json --output /tmp/finalgis-new-export --approve
/tmp/finalgis-build/finalgis-worker fiction --seed 42 --output /tmp/finalgis-new-fiction --approve
```

The fiction flag is `--seed 42` (separate argument). Output directories must not already exist. Add -DFINALGIS_SANITIZERS=ON in a separate build for ASan/UBSan. Public C17 header: src/finalgis.h. This worker runs independently from QGIS and never executes model-generated code.

Build/install Core's world-definition/ package. Export the scene through its canonical native validator:

```sh
python3 finalgis/scripts/export_fwd.py /tmp/finalgis-new-export --validator /path/to/fwd-prefix/bin/finalverse-fwd --source finalgis/fixtures/montreal
```

Assemble a separate branded desktop app and isolated profile from the pinned QGIS 3.44.15 LTR app:

```sh
python3 finalgis/scripts/package_app.py --qgis /path/to/QGIS.app --worker /tmp/finalgis-build/finalgis-worker --source finalgis/fixtures/montreal --output /path/to/new/FinalGIS.app --profile /path/to/new/finalgis-profile
```

macOS shortcuts: Command-Option1 professional GIS; Command-Option2 world engineering. Keep QGIS upstream attribution. QGIS 4.2.3 GUI has the documented macOS startup failure; its headless providers pass. The LTR desktop works. The desktop engine remains the pinned prebuilt foundation; the FinalGIS C++ worker and C17 app launcher are rebuilt. See [product identity and packaging acceptance](../docs/finalgis/OMEGA-XVII-0-ACCEPTANCE.md). No full QGIS source build, worldwide plugin parity, notarized distribution or accepted release is claimed.

See scripts/spatialdb_exchange.py for reviewed exchange through existing SpatialDB authored contracts. This creates an authored presentation asset with an advisory navigation anchor. Its exact projected CRS remains in FWD; it does not authorize or align a living-world mutation. The implementation and tested path are local macOS arm64. Production publication, full remote-provider acceptance and live MutSea associations remain separate gates.

For the verified service-to-renderer handoff, `scripts/readback_scene.py --help` accepts a pinned publication, private same-user token file, original FWD and canonical validator. It produces a static, material-bound FWD from authenticated finest-leaf readback. Only local HTTP/embedded untextured leaves are admitted; production/global streaming is a separate profile.

Ω-XVII.1 native workflow, publication and map-preview checkpoint: [current acceptance](../docs/finalgis/ACCEPTANCE.md). Native `workflow-plan` / `workflow-run` require exact plan-digest approval; `tool-registry` distinguishes the six bounded composite operations from deferred standalone tools.
