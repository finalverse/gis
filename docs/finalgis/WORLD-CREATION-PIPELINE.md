# World creation pipeline

workflow-plan validates a configured native model's recipe and binds the actual source inspection. workflow-run validates all fixed constraints and exact approval before generating a NEW output. Artifacts include scene.glb, content-addressed objects, workflow.json, geographic-plan.json and execution.json. Repeating the identical job checks existing receipt and asset integrity instead of generating another effect. Partial outputs are not treated as published.

The GLB exporter now emits finite normalized per-vertex normals for indexed geometry. Initial SpatialDB ingest correctly refused the old missing-normal output. Normals were added without changing any POSITION or index bytes; normal-geometry-preservation.json records the comparison. Generator metadata moved to0.2.0 and the plan pins the new executor profile. Final output is269,460bytes /5,046 triangles /8,589 vertices. Native tests validate unit normals and deterministic replay.

Existing canonical FWD export retains source licenses, hashes, version, world identity, projected frame/origin, geometry and synthetic/source-derived classifications. No new incompatible scene format or model-generated executable was introduced. This milestone does not generate water/land-cover that the fixture does not provide.
