#!/bin/sh
# Run from a root shell, or with sudo. Only manages this Compose project.
set -eu
cd "$(dirname "$0")/.."
docker compose config --quiet
docker compose up -d s3
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from verify import eventually, request
def ready():
    request("http://127.0.0.1:19000/health")
    return True
eventually("S3 ready", ready, timeout=120)
PY
python3 scripts/bootstrap.py
python3 scripts/verify_storage.py
docker compose up -d
python3 scripts/verify.py
