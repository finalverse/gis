"""Native workflow v2 scope/replay tests; actual GDAL execution, no mock GIS."""

import hashlib
import json
import math
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest

BIN, SOURCE = sys.argv[1:3]
sys.argv = sys.argv[:1]


class Workflow(unittest.TestCase):
    def call(self, *a, ok=True):
        r = subprocess.run(
            [BIN, *map(str, a)], capture_output=True, text=True, timeout=65
        )
        self.assertEqual(r.returncode == 0, ok, r.stderr)
        return json.loads(r.stdout) if ok else r.stderr

    def test_registry(self):
        r = self.call("tool-registry")
        self.assertEqual(len(r["tools"]), 16)
        self.assertEqual(
            sum(
                x["status"] == "supported_in_bounded_montreal_recipe"
                for x in r["tools"]
            ),
            6,
        )

    def test_scope_recovery_and_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            plan = self.call(
                "workflow-plan",
                "--source",
                SOURCE,
                "--request",
                "Prepare Montreal terrain and streets",
            )
            p = root / "plan.json"
            p.write_text(json.dumps(plan))
            args = [
                "workflow-run",
                "--source",
                SOURCE,
                "--plan",
                p,
                "--output",
                root / "out",
                "--approved-plan",
                plan["plan_id"],
            ]
            self.call(*args, ok=False)
            self.call(*args, "--approve", "--approved-plan", "bad", ok=False)
            for mutate in [
                "tool",
                "scope",
                "dataset",
                "authority",
                "units",
                "datum",
                "crs",
                "limits",
            ]:
                x = json.loads(json.dumps(plan))
                if mutate == "tool":
                    x["operation_sequence"][0]["tool"] = "shell.exec"
                if mutate == "scope":
                    x["authorization_scope"] = "publish_world"
                if mutate == "dataset":
                    x["input_dataset_references"]["source_bundle_recipe_sha256"] = (
                        "f" * 64
                    )
                if mutate == "authority":
                    x["owner"] = True
                if mutate == "units":
                    x["expected_units"] = "foot"
                if mutate == "datum":
                    x["expected_vertical_datum"] = "ellipsoidal"
                if mutate == "crs":
                    x["expected_crs"] = "EPSG:4326"
                if mutate == "limits":
                    x["execution_constraints"]["max_output_bytes"] = 2**40
                if mutate != "authority":
                    x.pop("plan_id")
                    x["plan_id"] = hashlib.sha256(
                        json.dumps(
                            x, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                        ).encode()
                    ).hexdigest()
                p.write_text(json.dumps(x))
                bad_args = list(args)
                bad_args[bad_args.index("--approved-plan") + 1] = x["plan_id"]
                self.call(*bad_args, "--approve", ok=False)
            self.assertFalse((root / "out").exists())
            p.write_text(json.dumps(plan))
            first = self.call(*args, "--approve")
            self.assertFalse(first["world_mutated"])
            self.assertFalse(first["replay"])
            raw = (root / "out/scene.glb").read_bytes()
            size = struct.unpack_from("<I", raw, 12)[0]
            doc = json.loads(raw[20 : 20 + size])
            binary = raw[28 + size :]
            for mesh in doc["meshes"]:
                for primitive in mesh["primitives"]:
                    normal = doc["accessors"][primitive["attributes"]["NORMAL"]]
                    view = doc["bufferViews"][normal["bufferView"]]
                    values = struct.unpack_from(
                        "<" + "f" * (normal["count"] * 3), binary, view["byteOffset"]
                    )
                    self.assertTrue(
                        all(
                            abs(math.sqrt(sum(x * x for x in values[i : i + 3])) - 1)
                            < 1e-5
                            for i in range(0, len(values), 3)
                        )
                    )
            again = self.call(*args, "--approve")
            self.assertTrue(again["replay"])
            self.assertEqual(first["asset"], again["asset"])
            data = (root / "out/scene.glb").read_bytes()
            (root / "out/scene.glb").write_bytes(data[:-1])
            self.call(*args, "--approve", ok=False)

    def test_provider_failure_is_not_ai_success(self):
        self.call(
            "workflow-plan",
            "--source",
            SOURCE,
            "--request",
            "Montreal",
            "--provider",
            "ollama",
            "--endpoint",
            "http://127.0.0.1:9",
            ok=False,
        )


if __name__ == "__main__":
    unittest.main()
