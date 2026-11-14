import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
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
        self.upgrade()
        self.assertEqual(env.read_text(), result)

    def test_partial_credentials_are_not_silently_replaced(self):
        env = self.root / ".env"
        original = "OTLP_USERNAME=existing-user\nGRAFANA_ADMIN_PASSWORD=keep-me\n"
        env.write_text(original)
        with self.assertRaises(SystemExit):
            self.upgrade()
        self.assertEqual(env.read_text(), original)


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
