import os
import subprocess
import sys

from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    def test_explicit_environment(self):
        env = dict(os.environ, DEBUG="False", ALLOWED_HOSTS="vet.test")
        result = subprocess.check_output([sys.executable, "-c",
            "from config.settings import DEBUG, ALLOWED_HOSTS; print(DEBUG, ALLOWED_HOSTS)"], env=env, text=True)
        self.assertEqual(result.strip(), "False ['vet.test']")

    def test_missing_secret(self):
        env = os.environ.copy()
        env.pop("SECRET_KEY", None)
        proc = subprocess.run([sys.executable, "-c", "import config.settings"], env=env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("SECRET_KEY", proc.stderr)
