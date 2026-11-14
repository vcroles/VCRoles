"""Bootstrap scoped storage users through stdin, keeping secrets out of argv."""

import io
import json
import subprocess
import zipfile

from verify import ROOT, settings


def user_archive(config):
    users = {
        f"vcroles-{service}": {
            "secretKey": config[f"{service.upper()}_S3_SECRET_KEY"],
            "status": "enabled",
        }
        for service in ("loki", "tempo", "mimir")
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("iam-assets/users.json", json.dumps(users))
    return output.getvalue()


def main():
    # No archive is persisted or printed, including on failure. Inherit the
    # caller's Compose environment/project selection, as up.sh does.
    result = subprocess.run(
        ["docker", "compose", "run", "--rm", "-T", "bootstrap"],
        input=user_archive(settings()),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=120,
    )
    if result.returncode:
        raise SystemExit(
            "Storage bootstrap failed; CLI output withheld to protect credentials"
        )
    print("Created private buckets, service-scoped users, and object quotas")


if __name__ == "__main__":
    main()
