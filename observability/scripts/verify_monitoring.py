"""Verify private host, container, database, and storage metrics on the host."""

import json
import subprocess
import urllib.parse

from verify import ROOT, eventually, request


def query(expression):
    params = urllib.parse.urlencode({"query": expression})
    return request(f"http://127.0.0.1:19009/prometheus/api/v1/query?{params}")["data"][
        "result"
    ]


def main():
    for name, expression in {
        "host CPU": 'node_cpu_seconds_total{job="host"}',
        "host memory": 'node_memory_MemAvailable_bytes{job="host"}',
        "host root filesystem": 'node_filesystem_avail_bytes{job="host",mountpoint="/"}',
        "bot container CPU": 'container_cpu_usage_seconds_total{job="containers",service="bot"}',
        "bot container memory": 'container_memory_working_set_bytes{job="containers",service="bot"}',
        "PostgreSQL exporter": 'pg_up{job="postgres"} == 1',
        "PostgreSQL database statistics": 'pg_stat_database_numbackends{job="postgres"}',
        "Redis exporter": 'redis_up{job="redis"} == 1',
        "Redis memory": 'redis_memory_used_bytes{job="redis"}',
        "RustFS native metrics": 'rustfs_api_requests_total{job="vcroles-storage"}',
        "RustFS bucket usage": 'rustfs_bucket_usage_usage_bytes{job="vcroles-storage"}',
        "Grafana SQLite pools": 'go_sql_open_connections{job="grafana"}',
    }.items():
        eventually(name, lambda expression=expression: query(expression), timeout=150)
    rows = query('container_memory_working_set_bytes{job="containers"}')
    services = {row["metric"]["service"] for row in rows}
    if (
        not {
            "bot",
            "postgres",
            "redis",
            "loki",
            "tempo",
            "mimir",
            "s3",
            "grafana",
            "alloy",
            "metrics-agent",
        }
        <= services
    ):
        raise RuntimeError("Expected container roles missing")
    if any(set(row["metric"]) & {"name", "id", "image"} for row in rows):
        raise RuntimeError("Raw container identity was not removed")
    if query('{job="vcroles-storage",path!=""}') or query(
        '{job="vcroles-storage",object!=""}'
    ):
        raise RuntimeError("Storage metrics retained object-path dimensions")
    print("PASS normalized container roles and storage label boundaries", flush=True)
    for filename in (
        "runtime.json",
        "app-databases.json",
        "observability-databases.json",
    ):
        dashboard = json.loads(
            (ROOT / "config/grafana/dashboards" / filename).read_text()
        )
        for panel in dashboard["panels"]:
            for target in panel.get("targets", []):
                expression = target["expr"].replace("$__rate_interval", "2m")
                # Idle ratios and percentiles legitimately have no observations,
                # and Python SDK metrics are optional. Required metric presence
                # is checked above; every panel must still execute successfully.
                query(expression)
        print(f"PASS dashboard query execution: {dashboard['title']}", flush=True)
    sockets = subprocess.check_output(
        ["ss", "-H", "-ltn", "sport", "=", ":12346"], text=True
    ).splitlines()
    if not sockets or any(line.split()[3] != "127.0.0.1:12346" for line in sockets):
        raise RuntimeError("Metrics-agent diagnostics are not loopback-only")
    print("PASS metrics-agent diagnostics bind to loopback only", flush=True)


if __name__ == "__main__":
    main()
