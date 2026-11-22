#!/usr/bin/env python3
"""Prepare a reviewed published scene in a NEW disposable authority copy."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for k in ["core", "config", "publication", "scene", "out"]:
    p.add_argument("--" + k, type=Path, required=True)
p.add_argument("--approve", action="store_true", required=True)
a = p.parse_args()
os.umask(0o077)
sys.path.insert(0, str(a.core / "scripts/omega-xv"))
from pipeline import (
    OWNER,
    REGION,
    WORLD,
    attachment,
    authority,
    compose,
    digest,
    feed_once,
    frozen_copy,
    load,
    run,
    write,
)

c = load(a.config)
status = load(a.publication / "state.json")
if (
    status["stage"] != "PUBLISHED"
    or digest(a.scene / "world.fwd.json") != status["identity"]["fwd_sha256"]
):
    raise ValueError("published immutable scene required")
a.out.mkdir(mode=0o700, parents=True, exist_ok=False)
sources = {
    "earth": frozen_copy(Path(c["earth"]), a.out / "episode"),
    "aetheria": frozen_copy(Path(c["aetheria"]), a.out / "aetheria"),
}
(a.out / "episode").chmod(0o700)
write(a.out / "source-hashes.json", sources)
write(
    a.out / "episode/omega-xiv-isolation.json",
    {
        "schema": "finalverse.omega-xiv-private-episode/1",
        "disposable": True,
        "source_hashes": sources["earth"],
    },
)
c.update(
    episode=str(a.out / "episode"),
    aetheria_copy=str(a.out / "aetheria"),
    projection=str(a.out / "projection.json"),
    coordination_lock=str(a.out / "coordination.lock"),
    world=WORLD,
    region=REGION,
    owner=OWNER,
)
initial = run([c["authority_xiv"], "inspect", c["episode"]], out=a.out / "initial.json")
write(a.out / "projection.json", initial["projection"])
pub = load(a.publication / "publication/publication.json")
readback = a.publication / "publication/readback"
doc = {
    "schema": "finalverse.scene-admission/0.1",
    "world": WORLD,
    "region": REGION,
    "owner": OWNER,
    "publication": {
        "graph": pub["graph_id"],
        "version": pub["version"],
        "fwd_sha256": digest(readback / "world.fwd.json"),
    },
    "registration_sha256": digest(c["geographic_registration"]),
    "presentation_only": True,
}
admitted = authority(c, "admit", doc, a.out / "admission.json")
again = authority(c, "admit", doc, a.out / "admission-replay.json")
assert admitted["receipt"] == again["receipt"]
c["attachment"] = str(attachment(c, a.scene, admitted, pub, a.out / "sdk-scene"))
feed_once(c, a.out / "feed", c["attachment"])
compose(
    c,
    readback,
    a.out / "feed",
    Path(c["geographic_registration"]),
    a.out / "registered",
)
c.update(
    registered=str(a.out / "registered"),
    admission=str(a.out / "admission.json"),
    readback=str(readback),
    publication=str(a.publication / "publication/publication.json"),
)
write(a.out / "config.json", c)
for name, source in [("earth", Path(c["earth"])), ("aetheria", Path(c["aetheria"]))]:
    for rel, expected in sources[name].items():
        assert hashlib.sha256((source / rel).read_bytes()).hexdigest() == expected
write(
    a.out / "preparation.json",
    {
        "schema": "finalgis.viewer-preparation/1",
        "original_worlds_unchanged": True,
        "admission_replay_identical": True,
        "binding": "owner-approved static reference in new disposable copy; presentation-only geographic registration",
        "source_plan_id": status["identity"]["plan_id"],
        "source_publication": pub["version"],
    },
)
print("prepared", a.out)
