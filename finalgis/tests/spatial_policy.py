"""Policy validation for typed AI spatial plans (no model, no network)."""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("si", Path(__file__).parents[1] / "services/spatial_intelligence.py")
si = importlib.util.module_from_spec(spec)
spec.loader.exec_module(si)
ds = {"id": "montreal", "crs": "EPSG:2950", "allowed_crs": ["EPSG:2950", "EPSG:4326"],
      "extent": [300489.3, 5040679.3, 300749.3, 5040939.3],
      "layers": [{"name": "terrain", "type": "raster"}, {"name": "roofs", "type": "polygon"}, {"name": "roads", "type": "line"}]}
op, route, q = si.validate_plan({"operation": "spatial.inspect_region", "arguments": {"bbox": [300500, 5040700, 300700, 5040900]}}, ds)
assert route == "inspect" and q == {"bbox": "300500.0,5040700.0,300700.0,5040900.0"}
op, route, q = si.validate_plan({"operation": "spatial.find_nearby", "arguments": {"x": 300619, "y": 5040809, "radius": 80, "layer": "roofs", "limit": 3}}, ds)
assert route == "nearby" and q["layer"] == "roofs"
bad = [
    {"operation": "world.delete_entity", "arguments": {}},
    {"operation": "spatial.inspect_region", "arguments": {"bbox": [1, 2, 3]}},
    {"operation": "spatial.inspect_region", "arguments": {"bbox": [0, 0, 10, 10]}},
    {"operation": "spatial.inspect_region", "arguments": {"bbox": [300500, 5040700, 300700, 5040900], "shell": "rm -rf /"}},
    {"operation": "spatial.find_nearby", "arguments": {"x": 300619, "y": 5040809, "radius": 99999}},
    {"operation": "spatial.find_nearby", "arguments": {"x": 300619, "y": 5040809, "layer": "terrain"}},
    {"operation": "spatial.find_nearby", "arguments": {"x": float("nan"), "y": 5040809}},
    {"operation": "spatial.find_nearby", "arguments": {"x": 300619, "y": 5040809, "crs": "EPSG:32618"}},
    {"operation": "spatial.find_nearby", "arguments": {"x": True, "y": 5040809}},
    ["not", "an", "object"],
]
for plan in bad:
    try:
        si.validate_plan(plan, ds)
    except si.PolicyError:
        continue
    sys.exit(f"admitted {plan}")
print("spatial policy tests passed")
