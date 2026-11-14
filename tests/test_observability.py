import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
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


if __name__ == "__main__":
    unittest.main()
