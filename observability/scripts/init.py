"""Generate local credentials and data directories; never prints secrets."""

import argparse
import ipaddress
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--grafana-bind", default="127.0.0.1")
    args = parser.parse_args()
    address = ipaddress.ip_address(args.grafana_bind)
    if not isinstance(address, ipaddress.IPv4Address):
        parser.error("Use an IPv4 loopback or Tailscale address")
    if not (address.is_loopback or address in ipaddress.ip_network("100.64.0.0/10")):
        parser.error("Grafana must bind to loopback or a Tailscale IPv4 address")
    env_path = ROOT / ".env"
    data = args.data_dir.resolve()
    if any(char.isspace() for char in str(data)):
        parser.error("Use a data directory without whitespace")
    if env_path.exists():
        raise SystemExit(".env already exists; existing credentials were preserved")
    values = {
        "DATA_DIR": str(data),
        "GRAFANA_BIND_IP": str(address),
        "GRAFANA_ROOT_URL": f"http://{address}:3300",
        "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(32),
        "S3_ROOT_ACCESS_KEY": "VCROLES" + secrets.token_hex(8).upper(),
        "S3_ROOT_SECRET_KEY": secrets.token_urlsafe(32),
        "LOKI_S3_SECRET_KEY": secrets.token_urlsafe(32),
        "TEMPO_S3_SECRET_KEY": secrets.token_urlsafe(32),
        "MIMIR_S3_SECRET_KEY": secrets.token_urlsafe(32),
    }
    # These commands are confined to the newly selected telemetry data path.
    # Docker's services use non-root UIDs and cannot initialize root-owned binds.
    for name in ("s3", "s3-logs", "alloy", "loki", "tempo", "mimir", "grafana"):
        uid = "472" if name == "grafana" else "10001"
        cmd = ["install", "-d", "-m", "0750", "-o", uid, "-g", uid, str(data / name)]
        if os.geteuid() != 0:
            cmd = ["sudo", "-n", *cmd]
        subprocess.run(cmd, check=True)
    fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.writelines(f"{key}={value}\n" for key, value in values.items())
    print(f"Created {env_path} (0600) and private data directories")
    print(f"Grafana is configured to bind only to {address}:3300")


if __name__ == "__main__":
    main()
