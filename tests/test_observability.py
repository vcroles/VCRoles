import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


class CollectorCredentialTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / "observability/scripts/init.py"
        spec = importlib.util.spec_from_file_location("observability_init", source)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        root = patch.object(self.module, "ROOT", self.root)
        root.start()
        self.addCleanup(root.stop)

    def upgrade(self):
        output = io.StringIO()
        with (
            patch("sys.argv", ["init.py", "--upgrade-otlp-auth"]),
            redirect_stdout(output),
        ):
            self.module.main()
        return output.getvalue()

    def test_upgrade_preserves_existing_secrets_and_is_idempotent(self):
        env = self.root / ".env"
        original = (
            "GRAFANA_ADMIN_PASSWORD=existing-grafana-secret\nDATA_DIR=/private/data\n"
        )
        env.write_text(original)
        os.chmod(env, 0o644)
        output = self.upgrade()
        result = env.read_text()
        self.assertTrue(result.startswith(original))
        values = dict(line.split("=", 1) for line in result.splitlines() if line)
        self.assertGreaterEqual(len(values["OTLP_PASSWORD"]), 32)
        self.assertNotIn(values["OTLP_PASSWORD"], output)
        self.assertNotIn(values["OTLP_HTPASSWD"], output)
        self.assertEqual(env.stat().st_mode & 0o777, 0o600)
        os.chmod(env, 0o644)
        self.upgrade()
        self.assertEqual(env.read_text(), result)
        self.assertEqual(env.stat().st_mode & 0o777, 0o600)

    def test_partial_credentials_are_not_silently_replaced(self):
        env = self.root / ".env"
        original = "OTLP_USERNAME=existing-user\nGRAFANA_ADMIN_PASSWORD=keep-me\n"
        env.write_text(original)
        with self.assertRaises(SystemExit):
            self.upgrade()
        self.assertEqual(env.read_text(), original)
        self.assertEqual(env.stat().st_mode & 0o777, 0o600)


class StorageBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.scripts = Path(__file__).resolve().parents[1] / "observability/scripts"
        self.config = {
            f"{service.upper()}_S3_SECRET_KEY": f"test-only-{service}-" * 3
            for service in ("loki", "tempo", "mimir")
        }
        helper = types.ModuleType("verify")
        helper.ROOT = self.root
        helper.settings = lambda: self.config
        spec = importlib.util.spec_from_file_location(
            "storage_bootstrap", self.scripts / "bootstrap.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"verify": helper}):
            spec.loader.exec_module(self.module)

    def test_credentials_travel_only_in_stdin_archive(self):
        with (
            patch.object(self.module.subprocess, "run") as run,
            redirect_stdout(io.StringIO()) as output,
        ):
            run.return_value.returncode = 0
            self.module.main()
        argv = run.call_args.args[0]
        self.assertEqual(argv, ["docker", "compose", "run", "--rm", "-T", "bootstrap"])
        with zipfile.ZipFile(io.BytesIO(run.call_args.kwargs["input"])) as archive:
            self.assertEqual(archive.namelist(), ["iam-assets/users.json"])
            users = json.loads(archive.read("iam-assets/users.json"))
        self.assertEqual(set(users), {"vcroles-loki", "vcroles-tempo", "vcroles-mimir"})
        for service in ("loki", "tempo", "mimir"):
            secret = self.config[f"{service.upper()}_S3_SECRET_KEY"]
            self.assertEqual(users[f"vcroles-{service}"]["secretKey"], secret)
            self.assertEqual(users[f"vcroles-{service}"]["status"], "enabled")
            self.assertNotIn(secret, str(argv) + output.getvalue())
        self.assertFalse(list(self.root.iterdir()))

    def test_bootstrap_failure_does_not_echo_cli_output(self):
        secret = self.config["LOKI_S3_SECRET_KEY"]
        with (
            patch.object(self.module.subprocess, "run") as run,
            redirect_stdout(io.StringIO()) as output,
        ):
            run.return_value.returncode = 1
            run.return_value.stdout = secret.encode()
            with self.assertRaises(SystemExit) as failure:
                self.module.main()
        self.assertNotIn(secret, str(failure.exception) + output.getvalue())

    def test_shell_never_expands_credentials_into_rc_arguments(self):
        # Exercise shell expansion and stdin forwarding, rather than examining
        # the script text. The CLI shim records only arguments and archive keys.
        shim = self.root / "rc"
        shim.write_text(
            f"#!{sys.executable}\n"
            "import io, json, os, sys, zipfile\n"
            "record = {'args': sys.argv[1:]}\n"
            "assert os.environ['RC_HOST_local'] == "
            "'http://test-root-access:test-root-secret@s3:9000'\n"
            "if sys.argv[1:4] == ['admin', 'iam', 'import']:\n"
            "    with zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())) as archive:\n"
            "        record['users'] = sorted(json.loads(archive.read('iam-assets/users.json')))\n"
            "with open(os.environ['CAPTURE'], 'a') as stream:\n"
            "    stream.write(json.dumps(record) + '\\n')\n"
        )
        shim.chmod(0o700)
        capture = self.root / "capture.jsonl"
        result = subprocess.run(
            ["/bin/sh", str(self.scripts / "bootstrap.sh")],
            input=self.module.user_archive(self.config),
            env={
                **os.environ,
                "PATH": f"{self.root}{os.pathsep}{os.environ['PATH']}",
                "CAPTURE": str(capture),
                "S3_ROOT_ACCESS_KEY": "test-root-access",
                "S3_ROOT_SECRET_KEY": "test-root-secret",
            },
            capture_output=True,
            check=True,
            timeout=10,
        )
        records = [json.loads(line) for line in capture.read_text().splitlines()]
        self.assertEqual(
            records[0]["args"],
            [
                "admin",
                "iam",
                "import",
                "local",
                "--file",
                "-",
                "--conflict",
                "overwrite",
                "--yes",
            ],
        )
        self.assertEqual(
            records[0]["users"], ["vcroles-loki", "vcroles-mimir", "vcroles-tempo"]
        )
        self.assertEqual(
            sum(record["args"][:2] == ["bucket", "quota"] for record in records), 3
        )
        visible = capture.read_text() + result.stdout.decode() + result.stderr.decode()
        for secret in ["test-root-access", "test-root-secret", *self.config.values()]:
            self.assertNotIn(secret, visible)


class MonitoringConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        helper = types.ModuleType("verify")
        helper.ROOT = self.root
        helper.settings = lambda: {"DATA_DIR": str(self.root / "data")}
        source = (
            Path(__file__).resolve().parents[1]
            / "observability/scripts/configure_monitoring.py"
        )
        spec = importlib.util.spec_from_file_location(
            "monitoring_configuration", source
        )
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"verify": helper}):
            spec.loader.exec_module(self.module)
        self.targets = {
            "postgres_dsn": "postgresql://monitor:example@localhost/app",
            "redis_addr": "redis://localhost:6379",
            "redis_password": "literal$pass=word'",
            "bot_container": "example-bot",
            "postgres_container": "example-postgres",
            "redis_container": "example-redis",
        }
        self.input = self.root / "monitoring-targets.json"
        self.save()

    def save(self):
        self.input.write_text(json.dumps(self.targets))
        self.input.chmod(0o600)

    def configure(self, *args):
        output = io.StringIO()
        with (
            patch("sys.argv", ["configure_monitoring.py", *args]),
            patch.object(self.module.subprocess, "run"),
            redirect_stdout(output),
        ):
            self.module.main()
        return output.getvalue()

    def test_private_literal_credentials_and_overwrite_guard(self):
        output = self.configure()
        path = self.root / ".metrics.env"
        original = path.read_text()
        self.assertIn("REDIS_PASSWORD=literal$pass=word'\n", original)
        self.assertNotIn(self.targets["redis_password"], output)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(SystemExit):
            self.configure()
        self.assertEqual(path.read_text(), original)

    def test_failed_atomic_replacement_preserves_original(self):
        self.configure()
        path = self.root / ".metrics.env"
        original = path.read_bytes()
        self.targets["redis_password"] = "new-password"
        self.save()
        with (
            patch.object(self.module.os, "replace", side_effect=OSError),
            self.assertRaises(OSError),
        ):
            self.configure("--replace")
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(list(self.root.glob(".metrics-*")))

    def test_public_or_multiline_credential_files_are_rejected(self):
        self.input.chmod(0o644)
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            self.configure()
        self.save()
        self.targets["redis_password"] = "password\nEXTRA=injected"
        self.save()
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            self.configure()
        self.assertFalse((self.root / ".metrics.env").exists())

    def test_concurrent_destination_is_not_overwritten(self):
        output = self.root / ".metrics.env"

        def competing_writer(*args):
            output.write_text("preserve-concurrent-writer\n")
            raise FileExistsError

        with (
            patch.object(self.module.os, "link", side_effect=competing_writer),
            self.assertRaises(FileExistsError),
        ):
            self.configure()
        self.assertEqual(output.read_text(), "preserve-concurrent-writer\n")
        self.assertFalse(list(self.root.glob(".metrics-*")))


class PreparedBotEnvironmentTests(unittest.TestCase):
    setUp = MonitoringConfigurationTests.setUp
    save = MonitoringConfigurationTests.save

    def prepare(self, config, *args):
        source = (
            Path(__file__).resolve().parents[1]
            / "observability/scripts/prepare_bot_environment.py"
        )
        spec = importlib.util.spec_from_file_location(
            "prepared_bot_configuration", source
        )
        module = importlib.util.module_from_spec(spec)
        helper = types.ModuleType("verify")
        helper.ROOT = self.root
        helper.settings = lambda: config
        output = io.StringIO()
        with (
            patch.dict(
                sys.modules, {"verify": helper, "configure_monitoring": self.module}
            ),
            patch("sys.argv", ["prepare_bot_environment.py", *args]),
            redirect_stdout(output),
        ):
            spec.loader.exec_module(module)
            module.main()
        return output.getvalue()

    def config(self):
        import ipaddress

        return {
            "GRAFANA_BIND_IP": str(
                ipaddress.ip_network("100.64.0.0/10").network_address + 1
            ),
            "OTLP_USERNAME": "vcroles",
            "OTLP_PASSWORD": "a" * 43,
        }

    def test_private_proposal_preserves_existing_application_settings(self):
        application = self.root / ".env"
        application.write_text("DATABASE_URL=preserve-existing-settings\n")
        config = self.config()
        output = self.prepare(config)
        candidate = self.root / ".bot-telemetry.env"
        self.assertEqual(candidate.stat().st_mode & 0o777, 0o600)
        self.assertIn("VCROLES_OTEL_ENABLED=1\n", candidate.read_text())
        self.assertNotIn(config["OTLP_PASSWORD"], output)
        self.assertNotIn(config["GRAFANA_BIND_IP"], output)
        self.assertEqual(
            application.read_text(), "DATABASE_URL=preserve-existing-settings\n"
        )
        with self.assertRaises(SystemExit):
            self.prepare(config)

    def test_public_and_loopback_addresses_are_rejected(self):
        for address in ("0.0.0.0", "127.0.0.1", "::1", "192.0.2.1"):
            config = {**self.config(), "GRAFANA_BIND_IP": address}
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                self.prepare(config)
        self.assertFalse((self.root / ".bot-telemetry.env").exists())

    def test_successful_replacement_keeps_private_permissions(self):
        config = self.config()
        self.prepare(config)
        config["OTLP_PASSWORD"] = "b" * 43
        self.prepare(config, "--replace", "--environment", "staging")
        path = self.root / ".bot-telemetry.env"
        self.assertIn("VCROLES_OTEL_ENVIRONMENT=staging\n", path.read_text())
        self.assertIn(config["OTLP_PASSWORD"], path.read_text())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_malformed_credentials_and_environment_are_rejected(self):
        config = self.config()
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            self.prepare({**config, "OTLP_PASSWORD": "short"})
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            self.prepare(config, "--environment", "invalid\nINJECTED=value")
        self.assertFalse((self.root / ".bot-telemetry.env").exists())


if __name__ == "__main__":
    unittest.main()
