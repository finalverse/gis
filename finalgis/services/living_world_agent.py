#!/usr/bin/env python3
"""Ω-XVII.3 AI-native world interaction agent.

The Living World Viewer writes a bounded request (finalverse.living-request/0.1)
into a private directory. This agent answers with finalverse.living-status/0.1:

    intent ─► local model proposes a TYPED world plan (JSON schema, temperature 0)
           ─► policy validates every step (allow-list, exact arguments, bounds,
              residents must exist in the authoritative snapshot)
           ─► deterministic execution
                 world.find_resident        authoritative MutSea snapshot (replication stream)
                 spatial.nearby_resident    resident position ─► registration (PROJ) ─►
                                            Map Server GEOS nearest features
                 world.move_resident        MutSea command gateway, agent token with the
                                            Modify scope only; MutSea policy authorizes
           ─► status with the verified answer

The model never receives a token, a URL or a callable tool, and its text is never
shown as a result. Registration accuracy is reported exactly as declared: with a
presentation-only registration, proximity is labelled as presentation proximity,
not surveyed distance.
"""

import argparse
import ctypes
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spatial_intelligence as si  # noqa: E402

OPERATIONS = {
    "world.find_resident": {"required": {"resident"}, "optional": set()},
    "spatial.nearby_resident": {"required": {"resident"}, "optional": {"radius", "layer", "limit"}},
    "world.move_resident": {"required": {"resident", "east_m", "north_m"}, "optional": set()},
}
MAX_STEPS = 3
MAX_MOVE_M = 20.0


class PolicyError(ValueError):
    pass


def private_dir(p):
    st = os.stat(p)
    return os.path.isdir(p) and st.st_uid == os.getuid() and (st.st_mode & 0o077) == 0


def write_private(path, obj):
    tmp = str(path) + ".part"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


class Registration:
    """region-local ⇄ EPSG:2950 through Core's libworld_convergence (PROJ pipeline)."""

    def __init__(self, lib, path, world, region):
        self.raw = Path(path).read_bytes()
        doc = json.loads(self.raw)
        self.doc = doc
        self.revision = int(doc["revision"])
        self.origin = doc["source"]["origin"]
        self.surveyed = bool(doc["validation"]["surveyed"])
        self.status = doc["validation"]["status"]
        self.scope = doc["authorization"]["scope"]
        self.lib = ctypes.CDLL(lib)
        self.handle = ctypes.c_void_p()
        err = ctypes.create_string_buffer(256)
        self.lib.fv_wc_registration_open.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint64,
                                                     ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p, ctypes.c_size_t]
        self.lib.fv_wc_to_asset.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
        if self.lib.fv_wc_registration_open(self.raw, len(self.raw), world.encode(), region.encode(), self.revision, ctypes.byref(self.handle), err, 256):
            raise RuntimeError("registration refused: " + err.value.decode())

    def region_to_crs(self, xyz):
        src = (ctypes.c_double * 3)(*xyz)
        out = (ctypes.c_double * 3)()
        if self.lib.fv_wc_to_asset(self.handle, self.revision, src, out):
            raise RuntimeError("position outside the registration")
        return [out[0] + self.origin[0], out[1] + self.origin[1], out[2] + self.origin[2]]

    @property
    def label(self):
        return "surveyed" if self.surveyed else f"presentation-only ({self.status}, not surveyed)"


class World:
    def __init__(self, mutsea, data):
        self.mutsea, self.data = mutsea, data

    def residents(self):
        """Authoritative residents from a fresh replication snapshot."""
        out = subprocess.run([self.mutsea, "live-follow", "--data", self.data, "--seconds", "1.0", "--dump"], capture_output=True, text=True, timeout=30)
        res = {}
        for line in out.stdout.splitlines():
            m = re.match(r'ENTITY (\S+) "AI resident · ([^·"]+?) ·[^"]*" owner=\S+ pos=\(([-\d.]+),([-\d.]+),([-\d.]+)\) rev=(\d+)', line)
            if m:
                res[m.group(2).strip().lower()] = {"id": m.group(1), "name": m.group(2).strip(), "pos": [float(m.group(3)), float(m.group(4)), float(m.group(5))], "revision": int(m.group(6))}
        head = re.search(r'"revision":(\d+)', out.stdout.splitlines()[-1]) if out.stdout else None
        return res, int(head.group(1)) if head else None

    def move(self, entity, to):
        r = subprocess.run([self.mutsea, "live-act", "--data", self.data, "--entity", entity, "--to", ",".join(f"{v:.3f}" for v in to), "--as", "agent"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or "MutSea refused the move")
        return json.loads(r.stdout)


def propose(request, residents, selected, model, ollama):
    schema = {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "maxItems": MAX_STEPS,
                "items": {
                    "type": "object",
                    "properties": {"operation": {"type": "string", "enum": sorted(OPERATIONS)}, "arguments": {"type": "object"}},
                    "required": ["operation", "arguments"],
                },
            },
            "rationale": {"type": "string"},
        },
        "required": ["steps", "rationale"],
    }
    ops = {
        "world.find_resident": '{"resident": name} locate a resident',
        "spatial.nearby_resident": '{"resident": name, "radius": metres 1-200, "layer": "roofs" (buildings) or "roads", "limit": 1-10} nearest map features around a resident',
        "world.move_resident": '{"resident": name, "east_m": number, "north_m": number} propose moving a resident; each component between -20 and 20 metres',
    }
    prompt = (
        "You plan actions in a persistent 3D world. Output a JSON plan of at most 3 steps using only these operations.\n"
        f"Operations: {json.dumps(ops)}\nResidents: {json.dumps(sorted(r['name'] for r in residents.values()))}\n"
        f"Currently selected resident: {selected or 'none'}\nRequest: {request}"
    )
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": schema, "options": {"temperature": 0, "seed": 7}, "keep_alive": "60m"}).encode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    started = time.time()
    with opener.open(urllib.request.Request(ollama.rstrip("/") + "/api/generate", body, {"Content-Type": "application/json"}), timeout=300) as r:
        raw = json.loads(r.read())["response"]
    return json.loads(raw), raw, time.time() - started


def validate(plan, residents, layers):
    if not isinstance(plan, dict) or set(plan) - {"steps", "rationale"} or not isinstance(plan.get("steps"), list):
        raise PolicyError("plan must be {steps, rationale}")
    if not 1 <= len(plan["steps"]) <= MAX_STEPS:
        raise PolicyError(f"a plan has 1..{MAX_STEPS} steps")
    canonical = []
    for i, step in enumerate(plan["steps"]):
        if not isinstance(step, dict) or set(step) != {"operation", "arguments"}:
            raise PolicyError(f"step {i + 1} must be {{operation, arguments}}")
        op, args = step["operation"], step["arguments"]
        if op not in OPERATIONS:
            raise PolicyError(f"operation {op!r} is not on the allow-list")
        if not isinstance(args, dict):
            raise PolicyError("arguments must be an object")
        spec = OPERATIONS[op]
        missing, extra = spec["required"] - set(args), set(args) - spec["required"] - spec["optional"]
        if missing or extra:
            raise PolicyError(f"{op}: missing {sorted(missing)} unexpected {sorted(extra)}")
        name = args["resident"]
        if not isinstance(name, str) or name.strip().lower() not in residents:
            raise PolicyError(f"{op}: {name!r} is not a resident of this world")
        c = {"operation": op, "resident": name.strip().lower()}

        def num(v, lo, hi, what):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or not lo <= v <= hi:
                raise PolicyError(f"{op}: {what} must be within [{lo}, {hi}]")
            return float(v)

        if op == "spatial.nearby_resident":
            c["radius"] = num(args.get("radius", 60), 1, 200, "radius")
            c["layer"] = args.get("layer", "roofs")
            if c["layer"] not in layers:
                raise PolicyError(f"layer {c['layer']!r} is not a vector layer")
            lim = args.get("limit", 5)
            if not isinstance(lim, int) or isinstance(lim, bool) or not 1 <= lim <= 10:
                raise PolicyError("limit must be an integer 1..10")
            c["limit"] = lim
        if op == "world.move_resident":
            c["east_m"] = num(args["east_m"], -MAX_MOVE_M, MAX_MOVE_M, "east_m")
            c["north_m"] = num(args["north_m"], -MAX_MOVE_M, MAX_MOVE_M, "north_m")
            if c["east_m"] == 0 and c["north_m"] == 0:
                raise PolicyError("a move must change the position")
        canonical.append(c)
    return canonical


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--interaction", required=True, help="private request/status directory shared with the Viewer")
    p.add_argument("--mutsea", required=True, help="mutsea binary")
    p.add_argument("--data", required=True, help="the live region directory (live-tokens.json)")
    p.add_argument("--registration", required=True)
    p.add_argument("--convergence-lib", required=True)
    p.add_argument("--endpoint", required=True, help="Map Server base URL (loopback)")
    p.add_argument("--map-token-file", type=Path, required=True)
    p.add_argument("--dataset", default="montreal")
    p.add_argument("--model", default="gemma4:e4b")
    p.add_argument("--ollama", default="http://127.0.0.1:11434")
    p.add_argument("--log", type=Path)
    a = p.parse_args()
    if not private_dir(a.interaction):
        sys.exit("interaction directory must be owner-private")
    if not a.endpoint.startswith(("http://127.0.0.1:", "http://[::1]:")):
        sys.exit("Map Server endpoint must be loopback")
    tokens = json.loads((Path(a.data) / "live-tokens.json").read_text())
    reg = Registration(a.convergence_lib, a.registration, tokens["world"], tokens["region"])
    map_token = a.map_token_file.read_text().strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(path):
        req = urllib.request.Request(a.endpoint + path, headers={"Authorization": "Bearer " + map_token})
        with opener.open(req, timeout=60) as r:
            return json.loads(r.read())

    dataset = get("/v1/catalog/" + a.dataset)
    layers = [l["name"] for l in dataset["layers"] if l["type"] != "raster"]
    world = World(a.mutsea, a.data)
    req_path, status_path = Path(a.interaction) / "request.json", Path(a.interaction) / "status.json"
    seen = None
    print(f"AGENT ready · model {a.model} · dataset {dataset['id']} {dataset['version'][:12]} · registration {reg.label}", flush=True)
    while True:
        time.sleep(0.2)
        try:
            raw = req_path.read_text()
            req = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if req.get("id") == seen:
            continue
        seen = req.get("id")
        if req.get("schema") != "finalverse.living-request/0.1" or req.get("world") != tokens["world"] or req.get("region") != tokens["region"] or len(req.get("text", "")) > 1024:
            write_private(status_path, {"schema": "finalverse.living-status/0.1", "id": seen, "stage": "refused", "title": "Request refused", "answer": "The request is malformed or names another world."})
            continue
        record = {"schema": "finalverse.living-agent-record/1", "id": seen, "request": req["text"], "model": a.model, "registration": reg.label}
        status = {"schema": "finalverse.living-status/0.1", "id": seen, "title": req["text"]}

        def emit(**kw):
            status.update(kw)
            write_private(status_path, status)

        try:
            residents, head = world.residents()
            selected = next((r["name"] for r in residents.values() if r["id"] == req.get("selected_entity")), None)
            emit(stage="planning", answer=f"{a.model} is proposing a typed plan…")
            plan, model_raw, model_s = propose(req["text"], residents, selected, a.model, a.ollama)
            record.update({"model_output": model_raw, "model_seconds": round(model_s, 2), "proposed_plan": plan})
            emit(stage="validating", plan=plan, answer="Policy is checking the proposed plan…")
            steps = validate(plan, residents, layers)
            record["policy"] = {"accepted": True, "steps": steps}
            policy_line = f"Typed plan from {a.model} ({model_s:.1f} s) · {len(steps)} step(s) accepted by policy · executed deterministically · registration {reg.label}"
            emit(stage="executing", policy=policy_line, answer="Executing validated steps…")
            answers, results, focus, executed = [], [], None, []
            for s in steps:
                r = residents[s["resident"]]
                focus = r["id"]
                if s["operation"] == "world.find_resident":
                    answers.append(f"{r['name']} is at region ({r['pos'][0]:.1f}, {r['pos'][1]:.1f}) m, entity revision {r['revision']} (authoritative MutSea snapshot).")
                    executed.append({"operation": s["operation"], "entity": r["id"], "position": r["pos"]})
                elif s["operation"] == "spatial.nearby_resident":
                    x, y, _ = reg.region_to_crs(r["pos"])
                    op, route, query = si.validate_plan({"operation": "spatial.find_nearby", "arguments": {"x": x, "y": y, "radius": s["radius"], "layer": s["layer"], "limit": s["limit"]}}, dataset)
                    out = get(f"/v1/spatial/{a.dataset}/{route}?" + urllib.parse.urlencode(query))
                    verified = out.get("operation") == op and out.get("dataset_version") == dataset["version"] and out.get("deterministic") is True
                    feats = out.get("features", [])
                    kind = "buildings" if s["layer"] == "roofs" else "road segments"
                    proximity = "surveyed distance" if reg.surveyed else "presentation proximity (registration not surveyed)"
                    answers.append(f"{out.get('matches', len(feats))} {kind} within {s['radius']:.0f} m of {r['name']} by {proximity}.")
                    for f in feats[: s["limit"]]:
                        attrs = f.get("attributes", {})
                        ident = attrs.get("ID_UEV") or attrs.get("OBJECTID") or attrs.get("id") or f.get("fid")
                        results.append(f"{s['layer'][:-1] if s['layer'].endswith('s') else s['layer']} {ident} · {f.get('distance_m', f.get('distance', 0)):.1f} m")
                    executed.append({"operation": s["operation"], "entity": r["id"], "query_crs_xy": [x, y], "map_query": query, "result_count": len(feats), "verified": verified, "dataset_version": dataset["version"]})
                elif s["operation"] == "world.move_resident":
                    to = [r["pos"][0] + s["east_m"], r["pos"][1] + s["north_m"], r["pos"][2]]
                    act = world.move(r["id"], to)
                    answers.append(f"MutSea committed {r['name']}'s move of {math.hypot(s['east_m'], s['north_m']):.1f} m (durable ack {act['durable_ack_ms']:.0f} ms) under the agent mandate.")
                    executed.append({"operation": s["operation"], "entity": r["id"], "to": to, "applied": act["applied"], "receipt": act["receipt"]})
            record["executed"] = executed
            emit(stage="done", answer=" ".join(answers), results=results, focus_entity=focus, policy=policy_line)
        except PolicyError as e:
            record["policy"] = {"accepted": False, "reason": str(e)}
            emit(stage="refused", answer=f"Policy refused the model's plan: {e}. Nothing was executed.", policy="Model output is a proposal only")
        except Exception as e:  # noqa: BLE001 - report, never crash the agent
            record["error"] = str(e)
            emit(stage="error", answer=f"Could not complete: {e}")
        record["status"] = status
        if a.log:
            with open(a.log, "a") as f:
                f.write(json.dumps(record) + "\n")
        print(f"AGENT {status['stage']} · {req['text'][:60]} · {status.get('answer', '')[:120]}", flush=True)


if __name__ == "__main__":
    main()
