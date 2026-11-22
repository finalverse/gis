# GIS tool registry

`finalgis-worker tool-registry` emits finalgis.gis-tools/1 with16 named operations, typed bounded input profiles, output metadata, units/CRS, effects, approval, limits, errors and provenance. Six are operational WITHIN the fixed native composite recipe: inspect_dataset, transform_crs, clip, buffer, validate_geometry and prepare_scene. The registry does not claim these are arbitrary standalone processing endpoints.

inspect_layers, inspect_extent, inspect_crs, intersect, union, reproject_raster, sample_elevation, inspect_topology, generate_terrain and preview_publication remain deferred standalone tools. Their schemas reject invocation. The composite internally samples elevation and generates terrain using mature native code; that does not create a separately exposed tool.

The compiled literal sequence, source digest and limits are checked independently of the JSON plan digest. Regression tests recompute candidate plan IDs before attempting CRS/unit/datum/scope/tool/budget tampering. No model-supplied authorizer or tool string can bypass those checks. Public C17 transformation ABI and existing FVP contracts remain unchanged.
