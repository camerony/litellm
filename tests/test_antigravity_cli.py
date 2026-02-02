
import sys
import unittest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

# import types
# # Mock dotenv before importing litellm
# sys.modules["dotenv"] = MagicMock()
# sys.modules["tiktoken"] = MagicMock()

# # Mock openai as a package
# openai_mock = types.ModuleType("openai")
# openai_mock._models = types.ModuleType("openai._models")
# # Add BaseModel to _models
# openai_mock._models.BaseModel = MagicMock()
# sys.modules["openai"] = openai_mock
# sys.modules["openai._models"] = openai_mock._models


# We need to ensure we can import the CLI
# Assuming PYTHONPATH is set
from litellm.proxy.proxy_cli import run_server

class TestAntigravityCLI(unittest.TestCase):
    @patch("litellm.llms.google_antigravity.auth.login")
    def test_login_command(self, mock_login):
        runner = CliRunner()
        result = runner.invoke(run_server, ["--login", "--provider", "google_antigravity"])
        
        if result.exit_code != 0:
            print(f"CLI Output: {result.output}")
            print(f"Exception: {result.exception}")

        self.assertEqual(result.exit_code, 0)
        mock_login.assert_called_once()

    def test_login_unsupported_provider(self):
        runner = CliRunner()
        result = runner.invoke(run_server, ["--login", "--provider", "invalid"])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("not supported for login", result.output)

if __name__ == "__main__":
    unittest.main()
