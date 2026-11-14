"""Create private metrics-agent settings from an operator-supplied JSON file.

Does not modify databases, containers, networks, or existing credentials.
"""

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

from verify import ROOT, settings


def write_private_environment(output, values, *, replace=False):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=output.parent, prefix=".metrics-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            stream.writelines(f"{key}={value}\n" for key, value in values.items())
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, output)
        else:
            # Publish atomically without clobbering a concurrently-created file.
            os.link(temporary, output)
        directory = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--targets", type=Path, default=ROOT / "monitoring-targets.json"
    )
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.targets.stat().st_mode & 0o077:
        parser.error("The targets file contains credentials; set its mode to 0600")
    targets = json.loads(args.targets.read_text())
    output = ROOT / ".metrics.env"
    if output.exists() and not args.replace:
        raise SystemExit(
            ".metrics.env already exists; use --replace for an intentional update"
        )
    values = {
        "POSTGRES_DSN": targets["postgres_dsn"],
        "REDIS_ADDR": targets["redis_addr"],
        "REDIS_PASSWORD": targets["redis_password"],
    }
    for key in ("bot", "postgres", "redis"):
        name = targets[f"{key}_container"].removeprefix("/")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name):
            parser.error("Invalid container name")
        values[f"{key.upper()}_CONTAINER_REGEX"] = "/?" + re.escape(name)
    if not all(
        isinstance(value, str) and value and not any(c in value for c in "\r\n\0")
        for value in values.values()
    ):
        parser.error("Metrics settings must be nonempty, single-line strings")
    data = Path(settings()["DATA_DIR"]) / "metrics-agent"
    subprocess.run(
        ["sudo", "-n", "install", "-d", "-m", "0750", "-o", "0", "-g", "0", str(data)],
        check=True,
    )
    write_private_environment(output, values, replace=args.replace)
    print("Created private metrics-agent settings (0600); no credentials printed")


if __name__ == "__main__":
    main()
