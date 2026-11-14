"""Send synthetic OTLP and verify all three backends and Grafana provisioning.

Run on the host. Uses the Python standard library and loopback-only APIs.
The generated evidence contains IDs and outcomes, never credentials.
"""

import argparse
import base64
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def settings():
    return dict(
        line.strip().split("=", 1)
        for line in (ROOT / ".env").read_text().splitlines()
        if line and not line.startswith("#")
    )


def request(url, payload=None, headers=None, *, method=None, timeout=10):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(headers or {}),
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode()
        return json.loads(body) if body.startswith(("{", "[")) else body


def collector_headers():
    config = settings()
    token = base64.b64encode(
        f"{config['OTLP_USERNAME']}:{config['OTLP_PASSWORD']}".encode()
    ).decode()
    return {"Authorization": f"Basic {token}"}


def verify_collector_auth():
    for signal in ("traces", "metrics", "logs"):
        for headers in ({}, {"Authorization": "Basic aW52YWxpZDppbnZhbGlk"}):
            try:
                request(f"http://127.0.0.1:4318/v1/{signal}", {}, headers)
            except urllib.error.HTTPError as error:
                if error.code not in (401, 403):
                    raise
            else:
                raise RuntimeError("OTLP receiver accepted missing/invalid credentials")
    print("PASS all HTTP OTLP signals reject missing/invalid credentials", flush=True)


def eventually(description, check, *, timeout=120):
    deadline = time.monotonic() + timeout
    error = None
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                print(f"PASS {description}", flush=True)
                return value
        except (OSError, ValueError, KeyError) as exc:
            error = type(exc).__name__
        time.sleep(2)
    raise RuntimeError(f"Timed out: {description}; last error type={error}")


def attributes(**values):
    return [
        {"key": key, "value": {"stringValue": str(value)}}
        for key, value in values.items()
    ]


def emit():
    run = secrets.token_hex(8)
    trace = secrets.token_hex(16)
    root, client, server = (secrets.token_hex(8) for _ in range(3))
    now = time.time_ns()
    start = now - 1_000_000_000

    def resource(service):
        return {
            "attributes": attributes(
                **{
                    "service.name": service,
                    "service.version": "infrastructure-validation",
                    "deployment.environment.name": "validation",
                }
            )
        }

    def span(name, span_id, parent, kind):
        result = {
            "traceId": trace,
            "spanId": span_id,
            "name": name,
            "kind": kind,
            "startTimeUnixNano": str(start),
            "endTimeUnixNano": str(start + 125_000_000),
            "status": {"code": 1},
            "flags": 1,
            "attributes": attributes(**{"validation.run": run}),
        }
        if parent:
            result["parentSpanId"] = parent
        return result

    traces = {
        "resourceSpans": [
            {
                "resource": resource("vcroles-validation"),
                "scopeSpans": [
                    {
                        "scope": {"name": "vcroles.validation"},
                        "spans": [
                            span("validation.request", root, None, 2),
                            span("validation.dependency", client, root, 3),
                        ],
                    }
                ],
            },
            {
                "resource": resource("vcroles-validation-dependency"),
                "scopeSpans": [
                    {
                        "scope": {"name": "vcroles.validation"},
                        "spans": [span("validation.dependency", server, client, 2)],
                    }
                ],
            },
        ]
    }
    logs = {
        "resourceLogs": [
            {
                "resource": resource("vcroles-validation"),
                "scopeLogs": [
                    {
                        "scope": {"name": "vcroles.validation"},
                        "logRecords": [
                            {
                                "timeUnixNano": str(now),
                                "severityNumber": 9,
                                "severityText": "INFO",
                                "body": {
                                    "stringValue": f"VCRoles telemetry validation {run}"
                                },
                                "traceId": trace,
                                "spanId": root,
                                "flags": 1,
                                "attributes": attributes(
                                    **{
                                        "event.name": "telemetry.validation",
                                        "validation.run": run,
                                    }
                                ),
                            }
                        ],
                    }
                ],
            }
        ]
    }
    metrics = {
        "resourceMetrics": [
            {
                "resource": resource("vcroles-validation"),
                "scopeMetrics": [
                    {
                        "scope": {"name": "vcroles.validation"},
                        "metrics": [
                            {
                                "name": "vcroles_validation_runs",
                                "unit": "1",
                                "sum": {
                                    "aggregationTemporality": 2,
                                    "isMonotonic": True,
                                    "dataPoints": [
                                        {
                                            "attributes": attributes(
                                                validation_run=run
                                            ),
                                            "startTimeUnixNano": str(start),
                                            "timeUnixNano": str(now),
                                            "asInt": "1",
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
    metrics["resourceMetrics"][0]["scopeMetrics"][0]["metrics"].append(
        {
            "name": "vcroles_validation_duration",
            "unit": "s",
            "histogram": {
                "aggregationTemporality": 2,
                "dataPoints": [
                    {
                        "attributes": attributes(validation_run=run),
                        "startTimeUnixNano": str(start),
                        "timeUnixNano": str(now),
                        "count": "1",
                        "sum": 0.125,
                        "explicitBounds": [0.01, 0.5, 1],
                        "bucketCounts": ["0", "1", "0", "0"],
                        "exemplars": [
                            {
                                "timeUnixNano": str(now),
                                "asDouble": 0.125,
                                "traceId": trace,
                                "spanId": root,
                            }
                        ],
                    }
                ],
            },
        }
    )
    for signal, payload in (("traces", traces), ("logs", logs), ("metrics", metrics)):
        result = request(
            f"http://127.0.0.1:4318/v1/{signal}", payload, collector_headers()
        )
        if isinstance(result, dict) and result.get("partialSuccess"):
            raise RuntimeError(f"OTLP {signal} was only partially accepted")
    return {"run": run, "trace_id": trace, "emitted_at_ns": now}


def verify(evidence, *, expect_exemplar=True):
    run, trace = evidence["run"], evidence["trace_id"]
    # Query the validation interval so restart checks don't depend on the
    # instant-query lookback window or on series still being actively exported.
    query_time = evidence["emitted_at_ns"] / 1e9 + 60
    eventually(
        "trace lookup", lambda: request(f"http://127.0.0.1:13200/api/traces/{trace}")
    )
    query = urllib.parse.urlencode(
        {
            "query": f'{{service_name="vcroles-validation"}} |= "{run}"',
            "start": str(evidence["emitted_at_ns"] - 1_000_000_000),
            "end": str(evidence["emitted_at_ns"] + 60_000_000_000),
        }
    )
    logs = eventually(
        "correlated log lookup",
        lambda: request(f"http://127.0.0.1:13100/loki/api/v1/query_range?{query}")[
            "data"
        ]["result"],
    )
    if not any(trace in json.dumps(stream) for stream in logs):
        raise RuntimeError("Log found without matching trace ID")
    query = urllib.parse.urlencode(
        {
            "query": f'vcroles_validation_runs{{validation_run="{run}"}}',
            "time": query_time,
        }
    )
    eventually(
        "OTLP metric lookup",
        lambda: request(f"http://127.0.0.1:19009/prometheus/api/v1/query?{query}")[
            "data"
        ]["result"],
    )
    graph = urllib.parse.urlencode(
        {
            "query": 'traces_service_graph_request_total{client="vcroles-validation",server="vcroles-validation-dependency"}',
            "time": query_time,
        }
    )
    eventually(
        "derived service graph metrics",
        lambda: request(f"http://127.0.0.1:19009/prometheus/api/v1/query?{graph}")[
            "data"
        ]["result"],
    )
    spanmetrics = urllib.parse.urlencode(
        {
            "query": 'traces_spanmetrics_calls{service_name="vcroles-validation"}',
            "time": query_time,
        }
    )
    eventually(
        "derived span metrics",
        lambda: request(
            f"http://127.0.0.1:19009/prometheus/api/v1/query?{spanmetrics}"
        )["data"]["result"],
    )
    exemplars = urllib.parse.urlencode(
        {
            "query": f'vcroles_validation_duration_bucket{{validation_run="{run}"}}',
            "start": evidence["emitted_at_ns"] / 1e9 - 1,
            "end": query_time,
        }
    )
    if expect_exemplar:
        eventually(
            "metric exemplar points to the trace",
            lambda: (
                trace
                in json.dumps(
                    request(
                        f"http://127.0.0.1:19009/prometheus/api/v1/query_exemplars?{exemplars}"
                    )["data"]
                )
            ),
        )
    config = settings()
    grafana = config["GRAFANA_ROOT_URL"]
    token = base64.b64encode(
        f"admin:{config['GRAFANA_ADMIN_PASSWORD']}".encode()
    ).decode()
    headers = {"Authorization": f"Basic {token}"}
    try:
        request(f"{grafana}/api/datasources")
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise
    else:
        raise RuntimeError(
            "Grafana datasource API unexpectedly allows anonymous access"
        )
    sources = request(f"{grafana}/api/datasources", headers=headers)
    if {s["uid"] for s in sources} != {"loki", "mimir", "tempo"}:
        raise RuntimeError("Expected all three provisioned Grafana data sources")
    for uid in ("loki", "mimir", "tempo"):
        result = request(f"{grafana}/api/datasources/uid/{uid}/health", headers=headers)
        if result.get("status") != "OK":
            raise RuntimeError(f"Grafana {uid} datasource health check failed")
    for uid in (
        "vcroles-telemetry",
        "vcroles-bot-health",
        "vcroles-runtime",
        "vcroles-app-databases",
        "vcroles-observability-databases",
    ):
        eventually(
            f"Grafana dashboard {uid}",
            lambda uid=uid: (
                request(f"{grafana}/api/dashboards/uid/{uid}", headers=headers)
                .get("dashboard", {})
                .get("panels")
            ),
        )
    expected_rules = json.loads(
        (ROOT / "config/grafana/provisioning/alerting/bot.json").read_text()
    )["groups"][0]["rules"]
    rules = {
        rule["uid"]: rule
        for rule in request(
            f"{grafana}/api/v1/provisioning/alert-rules", headers=headers
        )
    }
    for expected in expected_rules:
        rule = rules.get(expected["uid"])
        if rule is None or rule["isPaused"] != expected["isPaused"]:
            raise RuntimeError(
                "Alert rules do not match the provisioned activation state"
            )
    print(
        "PASS provisioned alert rules match their configured activation state",
        flush=True,
    )
    print(
        "PASS authenticated Grafana data sources and dashboard; anonymous access rejected",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-only",
        action="store_true",
        help="For controlled downstream-outage tests",
    )
    parser.add_argument(
        "--existing",
        action="store_true",
        help="Verify the last run after restarting the stack",
    )
    args = parser.parse_args()
    path = ROOT / "validation-results.json"
    if args.existing:
        evidence = json.loads(path.read_text())
    else:
        endpoints = {
            "Alloy": "http://127.0.0.1:12345/-/ready",
            "Loki": "http://127.0.0.1:13100/ready",
            "Tempo": "http://127.0.0.1:13200/ready",
            "Mimir": "http://127.0.0.1:19009/ready",
        }
        if args.emit_only:
            endpoints = {"Alloy": endpoints["Alloy"]}
        for name, url in endpoints.items():
            eventually(f"{name} ready", lambda url=url: request(url), timeout=180)
        verify_collector_auth()
        evidence = emit()
        path.write_text(json.dumps(evidence, indent=2) + "\n")
        print(f"PASS emitted synthetic OTLP; trace={evidence['trace_id']}", flush=True)
    if not args.emit_only:
        # Mimir exemplars live in memory/the WAL, not long-term S3 blocks. A
        # forced flush may retire their WAL before an archival restart test.
        verify(evidence, expect_exemplar=not args.existing)
        evidence["verified_at_ns"] = time.time_ns()
        path.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
