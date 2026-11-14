"""Check S3 persistence, service isolation, and a disposable bucket's hard quota."""

import datetime as dt
import hashlib
import hmac
import json
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from verify import ROOT, eventually, settings


def s3(method, bucket, *, key="", data=b"", access=None, secret=None, query=None):
    config = settings()
    access = access or config["S3_ROOT_ACCESS_KEY"]
    secret = secret or config["S3_ROOT_SECRET_KEY"]
    now = dt.datetime.now(dt.UTC)
    timestamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    path = urllib.parse.quote(f"/{bucket}" + (f"/{key}" if key else ""), safe="/~")
    query_string = urllib.parse.urlencode(
        sorted((query or {}).items()), quote_via=urllib.parse.quote
    )
    digest = hashlib.sha256(data).hexdigest()
    headers = {
        "Host": "127.0.0.1:19000",
        "X-Amz-Date": timestamp,
        "X-Amz-Content-Sha256": digest,
    }
    signed = "host;x-amz-content-sha256;x-amz-date"
    canonical_headers = f"host:{headers['Host']}\nx-amz-content-sha256:{digest}\nx-amz-date:{timestamp}\n"
    canonical = (
        f"{method}\n{path}\n{query_string}\n{canonical_headers}\n{signed}\n{digest}"
    )
    scope = f"{day}/us-east-1/s3/aws4_request"
    to_sign = f"AWS4-HMAC-SHA256\n{timestamp}\n{scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
    signing_key = ("AWS4" + secret).encode()
    for value in (day, "us-east-1", "s3", "aws4_request"):
        signing_key = hmac.new(signing_key, value.encode(), hashlib.sha256).digest()
    signature = hmac.new(signing_key, to_sign.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={access}/{scope}, SignedHeaders={signed}, Signature={signature}"
    )
    url = f"http://127.0.0.1:19000{path}" + (f"?{query_string}" if query_string else "")
    req = urllib.request.Request(
        url,
        data=data if method in {"PUT", "POST"} else None,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def main():
    config = settings()
    objects = {}
    for service, other in (("loki", "mimir"), ("tempo", "loki"), ("mimir", "tempo")):
        credentials = {
            "access": f"vcroles-{service}",
            "secret": config[f"{service.upper()}_S3_SECRET_KEY"],
        }
        raw = s3("GET", f"vcroles-{service}", query={"list-type": "2"}, **credentials)
        root = ET.fromstring(raw)
        objects[service] = len(root.findall("{*}Contents"))

        def round_trip(service=service, credentials=credentials):
            key = "validation/permission-probe"
            s3("PUT", f"vcroles-{service}", key=key, data=b"probe", **credentials)
            try:
                return (
                    s3("GET", f"vcroles-{service}", key=key, **credentials) == b"probe"
                )
            finally:
                s3("DELETE", f"vcroles-{service}", key=key, **credentials)

        eventually(f"{service} S3 read/write/delete", round_trip, timeout=60)
        try:
            s3("GET", f"vcroles-{other}", query={"list-type": "2"}, **credentials)
        except urllib.error.HTTPError as error:
            if error.code != 403:
                raise
        else:
            raise RuntimeError(
                f"{service} credentials can access another backend's bucket"
            )
    print(
        "PASS each backend can access its bucket and cannot access the others",
        flush=True,
    )
    try:
        urllib.request.urlopen("http://127.0.0.1:19000/vcroles-loki", timeout=10)
    except urllib.error.HTTPError as error:
        if error.code != 403:
            raise
    else:
        raise RuntimeError("S3 bucket unexpectedly allows anonymous access")
    print("PASS anonymous S3 access rejected", flush=True)
    bucket = "vcroles-quota-" + secrets.token_hex(4)
    s3("PUT", bucket)
    try:
        command = 'rc alias set local http://s3:9000 "$S3_ROOT_ACCESS_KEY" "$S3_ROOT_SECRET_KEY" >/dev/null && rc bucket quota set "local/$PROBE_BUCKET" 1M'
        result = subprocess.run(
            [
                "sudo",
                "-n",
                "docker",
                "compose",
                "run",
                "--rm",
                "-e",
                f"PROBE_BUCKET={bucket}",
                "--entrypoint",
                "/bin/sh",
                "bootstrap",
                "-c",
                command,
            ],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        if result.returncode:
            # Never echo admin command output, which could contain credentials.
            raise RuntimeError("Could not set the disposable bucket's quota")

        def write_small():
            # RustFS creates an authoritative quota ledger asynchronously. Its
            # first write can return 503 SlowDown until reconciliation finishes.
            s3("PUT", bucket, key="small", data=b"small object")
            return True

        eventually(
            "new quota ledger admits an in-budget write", write_small, timeout=60
        )
        if s3("GET", bucket, key="small") != b"small object":
            raise RuntimeError("S3 round trip failed")
        try:
            s3("PUT", bucket, key="large", data=b"x" * (2 * 1024 * 1024))
        except urllib.error.HTTPError as error:
            body = error.read().decode()
            if "quota" not in body.lower():
                raise RuntimeError(
                    f"Large write failed for a reason other than quota: HTTP {error.code}"
                ) from error
        else:
            s3("DELETE", bucket, key="large")
            raise RuntimeError("S3 quota did not reject an oversized write")
        print(
            "PASS small S3 round trip and oversized-write rejection at 1 MiB quota",
            flush=True,
        )
    finally:
        s3("DELETE", bucket, key="small")
        s3("DELETE", bucket)
    print(json.dumps({"stored_objects": objects}), flush=True)


if __name__ == "__main__":
    main()
