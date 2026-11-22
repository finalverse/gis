"""spatial.validate_registration: reproduce the pinned anchor; refuse tampering
and unsupported survey claims."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

worker, fixtures = sys.argv[1], Path(sys.argv[2])
reg = fixtures / "registration/geographic-registration.json"
geoid = fixtures / "registration/geoid.tif"


def run(doc):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "r.json"
        p.write_text(json.dumps(doc))
        r = subprocess.run([worker, "registration-validate", "--registration", str(p), "--geoid", str(geoid)], capture_output=True, text=True)
        return json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr}


base = json.loads(reg.read_text())
ok = run(base)
assert ok["verdict"] == "valid_presentation_only_registration", ok
assert ok["authoritative"] is False and ok["model"]["registration_revision"] == 1
assert all(c["pass"] for c in ok["checks"]), ok["checks"]
assert abs(ok["recomputed"]["geoid_undulation_m"] + 30.385) < 0.01

shifted = json.loads(json.dumps(base))
shifted["destination"]["wgs84_anchor_lon_lat_h"][0] += 1e-7  # about 8 mm east
assert run(shifted)["verdict"] == "invalid"
raised = json.loads(json.dumps(base))
raised["source"]["origin"][2] += 0.01
assert run(raised)["verdict"] == "invalid"
claim = json.loads(json.dumps(base))
claim["validation"]["surveyed"] = True
claim["authorization"]["scope"] = "authoritative"
r = run(claim)
assert r["verdict"] == "invalid" and r["registration_class"] == "invalid_surveyed_claim", r
scope = json.loads(json.dumps(base))
scope["authorization"]["scope"] = "authoritative"
assert run(scope)["verdict"] == "invalid"
grid = json.loads(json.dumps(base))
grid["pipeline"]["vertical_grid_sha256"] = "0" * 64
assert run(grid)["verdict"] == "invalid"
print("registration validation tests passed")
