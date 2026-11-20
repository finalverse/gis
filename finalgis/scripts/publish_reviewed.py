#!/usr/bin/env python3
"""Owner-local publication adapter to existing Core Forge/SpatialDB contracts.

Operator configuration is trusted executable configuration, not LLM input. No
MutSea admission/action function is called. Production endpoints are not used.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ["config", "scene", "out", "fixture", "core"]:
        p.add_argument("--" + n, type=Path, required=True)
    p.add_argument("--approved-plan", required=True)
    a = p.parse_args()
    os.umask(0o077)
    c = json.loads(a.config.read_text())
    plan = json.loads((a.scene / "geographic-plan.json").read_text())
    execution = json.loads((a.scene / "execution.json").read_text())
    if (
        plan["plan_id"] != a.approved_plan
        or execution["workflow_plan_id"] != a.approved_plan
        or execution["asset"]["sha256"] != h(a.scene / "scene.glb")
    ):
        raise ValueError("Reviewed plan/asset identity mismatch")
    # Revalidate the exact local plan, dataset and bounded scope through native code.
    worker = c["worker"]
    subprocess.run(
        [
            worker,
            "workflow-run",
            "--source",
            c["source"],
            "--plan",
            a.scene / "geographic-plan.json",
            "--output",
            a.scene,
            "--approved-plan",
            a.approved_plan,
            "--approve",
        ],
        check=True,
        capture_output=True,
        timeout=65,
    )
    here = Path(__file__).resolve().parent
    if not (a.scene / "world.fwd.json").exists():
        subprocess.run(
            [
                sys.executable,
                here / "export_fwd.py",
                a.scene,
                "--validator",
                c["fwd_validator"],
                "--source",
                c["source"],
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
    else:
        subprocess.run(
            [
                c["fwd_validator"],
                "validate",
                a.scene / "world.fwd.json",
                a.scene / "objects",
            ],
            check=True,
            capture_output=True,
            timeout=10,
        )
    fwd = a.scene / "world.fwd.json"
    identity = {"plan_id": a.approved_plan, "fwd_sha256": h(fwd)}
    if a.out.exists():
        status = json.loads((a.out / "state.json").read_text())
        if status["stage"] != "PUBLISHED" or status["identity"] != identity:
            raise ValueError("Incomplete or conflicting job; no automatic republish")
        readback = a.out / "publication/readback/world.fwd.json"
        if h(readback) != status["readback_sha256"]:
            raise ValueError("Persisted readback mismatch")
        subprocess.run(
            [c["fwd_validator"], "validate", readback, readback.parent / "objects"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        print(json.dumps(dict(status, replay=True)))
        return
    a.out.mkdir(mode=0o700, parents=True)

    def state(stage, **extra):
        d = {
            "schema": "finalgis.publication-state/1",
            "stage": stage,
            "identity": identity,
            "world_mutated": False,
            "authority": "existing Forge/SpatialDB, local disposable fixture only",
        }
        d.update(extra)
        tmp = a.out / "state.part"
        tmp.write_text(json.dumps(d, indent=2))
        tmp.replace(a.out / "state.json")
        return d

    state("DRAFT")
    state("VALIDATING")
    sys.path.insert(0, str(a.core / "scripts/omega-xv"))
    import pipeline

    c["finalgis"] = str(here.parents[1])
    state("VALIDATED")
    state("PUBLISHING")
    try:
        publication = pipeline.publish(
            c, fwd, a.scene / "objects", a.out / "publication", a.fixture
        )
        result = state(
            "PUBLISHED",
            publication=publication,
            readback_sha256=h(a.out / "publication/readback/world.fwd.json"),
            registration_status=plan["registration_status"],
            replay=False,
        )
        print(json.dumps(result))
    except Exception as error:
        state("FAILED", error=str(error))
        raise


if __name__ == "__main__":
    main()
