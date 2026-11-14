"""Explicit recovery test for this new stack; never restarts other containers."""

import argparse
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from verify import ROOT, eventually, request
from verify_storage import s3

PROJECT = "vcroles-observability"
SERVICES = ["s3", "loki", "tempo", "mimir", "alloy", "grafana"]
BACKENDS = ["loki", "tempo", "mimir"]


def compose(*args):
    subprocess.run(
        ["sudo", "-n", "docker", "compose", "-p", PROJECT, *args], cwd=ROOT, check=True
    )


def protected_snapshot():
    ids = subprocess.check_output(
        ["sudo", "-n", "docker", "ps", "-q"], text=True
    ).split()
    containers = (
        json.loads(subprocess.check_output(["sudo", "-n", "docker", "inspect", *ids]))
        if ids
        else []
    )
    return {
        c["Name"]: {
            "id": c["Id"],
            "started": c["State"]["StartedAt"],
            "pid": c["State"]["Pid"],
            "restarts": c["RestartCount"],
        }
        for c in containers
        if (c["Config"].get("Labels") or {}).get("com.docker.compose.project")
        != PROJECT
    }


def verify(*args):
    subprocess.run([sys.executable, str(ROOT / "scripts/verify.py"), *args], check=True)


def object_counts():
    return {
        service: len(
            ET.fromstring(
                s3("GET", f"vcroles-{service}", query={"list-type": "2"})
            ).findall("{*}Contents")
        )
        for service in BACKENDS
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-service-restarts", action="store_true")
    args = parser.parse_args()
    if not args.allow_service_restarts:
        parser.error(
            "Pass --allow-service-restarts to test only this Compose project's services"
        )
    before = protected_snapshot()
    evidence = {"started_at_ns": time.time_ns(), "protected_containers": sorted(before)}
    try:
        verify()
        request("http://127.0.0.1:13100/flush", method="POST")
        # The endpoint's return status alone is not proof of successful upload.
        # Verify actual objects afterwards for all three backends.
        request(
            "http://127.0.0.1:19009/ingester/flush?wait=true", method="POST", timeout=60
        )

        def objects_ready():
            counts = object_counts()
            return counts if all(counts.values()) else None

        evidence["object_counts"] = eventually(
            "all backends have written S3 objects",
            objects_ready,
            timeout=120,
        )
        compose("restart", "--timeout", "60", *SERVICES)
        verify("--existing")
        evidence["restart_persistence"] = True
        try:
            compose("stop", "--timeout", "60", *BACKENDS)
            verify("--emit-only")
            time.sleep(3)
        finally:
            compose("up", "-d", *BACKENDS)
        verify("--existing")
        evidence["downstream_outage_recovery"] = True
    finally:
        after = protected_snapshot()
        evidence["protected_containers_unchanged"] = before == after
        evidence["finished_at_ns"] = time.time_ns()
        (ROOT / "recovery-results.json").write_text(
            json.dumps(evidence, indent=2) + "\n"
        )
        if before != after:
            raise RuntimeError(
                "An unrelated container's runtime identity changed during validation"
            )
    print(
        "PASS restart persistence, downstream outage recovery, and unrelated containers unchanged",
        flush=True,
    )


if __name__ == "__main__":
    main()
