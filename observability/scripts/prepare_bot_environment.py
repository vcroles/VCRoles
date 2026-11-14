"""Prepare private bot telemetry settings; never applies them to the bot."""

import argparse
import ipaddress
import re

from configure_monitoring import write_private_environment
from verify import ROOT, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--environment", default="production")
    args = parser.parse_args()
    config = settings()
    try:
        address = ipaddress.ip_address(config["GRAFANA_BIND_IP"])
        if not isinstance(
            address, ipaddress.IPv4Address
        ) or address not in ipaddress.ip_network("100.64.0.0/10"):
            raise ValueError
    except (KeyError, ValueError):
        parser.error("A Tailscale IPv4 Grafana binding is required for this deployment")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", args.environment):
        parser.error("Invalid environment identifier")
    user, password = config["OTLP_USERNAME"], config["OTLP_PASSWORD"]
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", user) or not re.fullmatch(
        r"[a-zA-Z0-9_-]{32,128}", password
    ):
        parser.error("Use generated collector credentials")
    output = ROOT / ".bot-telemetry.env"
    if output.exists() and not args.replace:
        raise SystemExit(
            "Prepared bot settings already exist; use --replace for an intentional update"
        )
    write_private_environment(
        output,
        {
            "VCROLES_OTEL_ENABLED": "1",
            "OTEL_SERVICE_NAME": "vcroles",
            "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://{address}:4318",
            "VCROLES_OTEL_USERNAME": user,
            "VCROLES_OTEL_PASSWORD": password,
            "VCROLES_OTEL_ENVIRONMENT": args.environment,
        },
        replace=args.replace,
    )
    print("Prepared private bot environment (0600); production bot settings unchanged")


if __name__ == "__main__":
    main()
