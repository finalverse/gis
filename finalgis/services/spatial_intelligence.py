#!/usr/bin/env python3
"""Typed AI spatial operations over Finalverse Map Server (Ω-XVII.2).

AI intent -> typed plan -> policy validation -> deterministic tool -> result
verification. A local model may only *propose* one typed operation; this
module validates it against an allow-list and the dataset catalog, and only
then calls the Map Server, whose GDAL/OGR/GEOS code computes the answer. The
model never sees a tool it can call directly, never receives a token, and its
output is never treated as a result. Nothing here writes world state.
"""

import argparse
import json
import math
import sys
import urllib.request
from pathlib import Path

OPERATIONS = {
    "spatial.inspect_region": {"route": "inspect", "required": {"bbox"}, "optional": {"crs"}},
    "spatial.find_nearby": {"route": "nearby", "required": {"x", "y"}, "optional": {"crs", "radius", "layer", "limit"}},
}


class PolicyError(ValueError):
    pass


def validate_plan(plan, dataset):
    """Returns the canonical query for an admissible plan or raises PolicyError."""
    if not isinstance(plan, dict) or set(plan) - {"operation", "arguments", "rationale"}:
        raise PolicyError("plan must be an object with operation/arguments/rationale only")
    op = plan.get("operation")
    if op not in OPERATIONS:
        raise PolicyError(f"operation {op!r} is not on the allow-list")
    args = plan.get("arguments")
    if not isinstance(args, dict):
        raise PolicyError("arguments must be an object")
    spec = OPERATIONS[op]
    missing = spec["required"] - set(args)
    extra = set(args) - spec["required"] - spec["optional"]
    if missing or extra:
        raise PolicyError(f"arguments missing {sorted(missing)} or unexpected {sorted(extra)}")
    crs = args.get("crs", dataset["crs"])
    if crs not in dataset["allowed_crs"]:
        raise PolicyError(f"CRS {crs} is not offered by dataset {dataset['id']}")
    ext = dataset["extent"]
    query = {}
    if crs != dataset["crs"]:
        query["crs"] = crs

    def finite(v, name):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise PolicyError(f"{name} must be a finite number")
        return float(v)

    if op == "spatial.inspect_region":
        box = args["bbox"]
        if not isinstance(box, list) or len(box) != 4:
            raise PolicyError("bbox must have four numbers")
        box = [finite(v, "bbox") for v in box]
        if box[0] >= box[2] or box[1] >= box[3]:
            raise PolicyError("bbox must be ordered min,max")
        if crs == dataset["crs"] and (box[2] < ext[0] or box[0] > ext[2] or box[3] < ext[1] or box[1] > ext[3]):
            raise PolicyError("bbox does not intersect the dataset extent")
        query["bbox"] = ",".join(repr(v) for v in box)
    else:
        x, y = finite(args["x"], "x"), finite(args["y"], "y")
        if crs == dataset["crs"] and not (ext[0] - 500 <= x <= ext[2] + 500 and ext[1] - 500 <= y <= ext[3] + 500):
            raise PolicyError("point is not near the dataset")
        query["x"], query["y"] = repr(x), repr(y)
        if "radius" in args:
            r = finite(args["radius"], "radius")
            if not 0 < r <= 500:
                raise PolicyError("radius must be in (0, 500] metres")
            query["radius"] = repr(r)
        if "limit" in args:
            if not isinstance(args["limit"], int) or not 1 <= args["limit"] <= 50:
                raise PolicyError("limit must be an integer 1..50")
            query["limit"] = str(args["limit"])
        if "layer" in args:
            names = [l["name"] for l in dataset["layers"] if l["type"] != "raster"]
            if args["layer"] not in names:
                raise PolicyError("layer is not a vector layer of this dataset")
            query["layer"] = args["layer"]
    return op, OPERATIONS[op]["route"], query


def propose(request, dataset, model, ollama):
    """Asks a local model for one typed operation; returns (plan, raw)."""
    schema = {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": sorted(OPERATIONS)},
            "arguments": {"type": "object"},
            "rationale": {"type": "string"},
        },
        "required": ["operation", "arguments"],
    }
    context = {
        "dataset": dataset["id"],
        "crs": dataset["crs"],
        "extent_min_x_min_y_max_x_max_y": dataset["extent"],
        "layers": [{"name": l["name"], "type": l["type"]} for l in dataset["layers"]],
        "operations": {
            "spatial.inspect_region": 'arguments {"bbox": [minx, miny, maxx, maxy]} in dataset CRS metres; counts features, road length, roof area, terrain statistics',
            "spatial.find_nearby": 'arguments {"x": number, "y": number, "radius": metres up to 500, "layer": "roofs" or "roads" (may be omitted), "limit": integer 1-50 (may be omitted)} in dataset CRS; nearest features',
        },
    }
    prompt = (
        "You plan geographic queries. Choose exactly one operation and its arguments for the user's request. "
        "Coordinates are projected metres in the dataset CRS. Answer with JSON only.\n"
        f"Context: {json.dumps(context)}\nRequest: {request}"
    )
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": schema, "options": {"temperature": 0, "seed": 7}}).encode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(urllib.request.Request(ollama.rstrip("/") + "/api/generate", body, {"Content-Type": "application/json"}), timeout=240) as r:
        raw = json.loads(r.read())["response"]
    return json.loads(raw), raw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--endpoint", required=True, help="Map Server base URL (loopback)")
    p.add_argument("--token-file", type=Path, required=True)
    p.add_argument("--dataset", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--request", help="natural-language intent for the local model")
    g.add_argument("--plan", type=Path, help="an already typed plan (no model involved)")
    p.add_argument("--model", default="gemma4:e4b")
    p.add_argument("--ollama", default="http://127.0.0.1:11434")
    a = p.parse_args()
    if not a.endpoint.startswith(("http://127.0.0.1:", "http://[::1]:")):
        sys.exit("Map Server endpoint must be loopback for this tool")
    if a.token_file.stat().st_mode & 0o077:
        sys.exit("token file must be private")
    token = a.token_file.read_text().strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(path):
        req = urllib.request.Request(a.endpoint + path, headers={"Authorization": "Bearer " + token})
        with opener.open(req, timeout=60) as r:
            return json.loads(r.read())

    dataset = get("/v1/catalog/" + a.dataset)
    record = {"schema": "finalgis.spatial-intelligence-record/1", "dataset": dataset["id"], "dataset_version": dataset["version"]}
    if a.request:
        plan, raw = propose(a.request, dataset, a.model, a.ollama)
        record.update({"intent": a.request, "model": a.model, "model_output": raw})
    else:
        plan = json.loads(a.plan.read_text())
        record["model"] = None
    record["proposed_plan"] = plan
    try:
        op, route, query = validate_plan(plan, dataset)
    except PolicyError as e:
        record["policy"] = {"accepted": False, "reason": str(e)}
        print(json.dumps(record, indent=1))
        return 3
    record["policy"] = {"accepted": True, "operation": op, "query": query}
    from urllib.parse import urlencode

    result = get(f"/v1/spatial/{a.dataset}/{route}?" + urlencode(query))
    verified = result.get("operation") == op and result.get("dataset_version") == dataset["version"] and result.get("deterministic") is True
    record["result"] = result
    record["verification"] = {"operation_matches": result.get("operation") == op, "dataset_version_matches": result.get("dataset_version") == dataset["version"],
                              "deterministic_tool": result.get("deterministic") is True, "verified": verified}
    record["authority"] = "read-only geographic computation; no world state changed"
    print(json.dumps(record, indent=1))
    return 0 if verified else 4


if __name__ == "__main__":
    sys.exit(main())
