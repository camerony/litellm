
import os
import json
import unittest
import sys
from unittest.mock import MagicMock, patch

# Mock dotenv before importing litellm
# sys.modules["dotenv"] = MagicMock()
# sys.modules["tiktoken"] = MagicMock()
# import types

# # Mock openai as a package to handle submodule imports in litellm
# openai_mock = types.ModuleType("openai")
# openai_mock.types = types.ModuleType("openai.types")
# openai_mock._models = types.ModuleType("openai._models")
# openai_mock._models.BaseModel = MagicMock()
# openai_mock.lib = types.ModuleType("openai.lib")
# openai_mock.lib._parsing = types.ModuleType("openai.lib._parsing")
# openai_mock.lib._pydantic = types.ModuleType("openai.lib._pydantic")

# openai_mock.types.chat = types.ModuleType("openai.types.chat")
# openai_mock.types.chat.completion_create_params = types.ModuleType("openai.types.chat.completion_create_params")
# openai_mock.types.chat.completion_create_params.ResponseFormat = MagicMock()

# openai_mock._legacy_response = types.ModuleType("openai._legacy_response")
# openai_mock._legacy_response.HttpxBinaryResponseContent = MagicMock()

# # helper for APIConnectionError etc
# openai_mock.APIConnectionError = Exception
# openai_mock.AuthenticationError = Exception
# openai_mock.BadRequestError = Exception
# openai_mock.NotFoundError = Exception
# openai_mock.RateLimitError = Exception
# openai_mock.APITimeoutError = Exception
# openai_mock.OpenAIError = Exception
# openai_mock.Omit = MagicMock()


# sys.modules["openai"] = openai_mock
# sys.modules["openai.types"] = openai_mock.types
# sys.modules["openai._models"] = openai_mock._models
# sys.modules["openai.lib"] = openai_mock.lib
# sys.modules["openai.lib._parsing"] = openai_mock.lib._parsing
# sys.modules["openai.lib._pydantic"] = openai_mock.lib._pydantic
# sys.modules["openai.types.chat"] = openai_mock.types.chat
# sys.modules["openai.types.chat.completion_create_params"] = openai_mock.types.chat.completion_create_params
# sys.modules["openai._legacy_response"] = openai_mock._legacy_response


from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion
import litellm

# Mock auth file content
AUTH_FILE_CONTENT = {
    "profiles": {
        "test-profile": {
            "type": "oauth",
            "provider": "google-antigravity",
            "access": "old-token",
            "refresh": "refresh-token",
            "expires": 0, # Expired
            "email": "test@example.com",
            "projectId": "test-project"
        }
    }
}

class TestAntigravity(unittest.TestCase):
    @patch("litellm.llms.google_antigravity.chat.handler.httpx.post")
    @patch("litellm.llms.google_antigravity.chat.handler.open")
    @patch("litellm.llms.google_antigravity.chat.handler.os.path.exists")
    @patch("litellm.llms.google_antigravity.chat.handler.SimpleFileLock")
    def test_antigravity_flow(self, mock_lock, mock_exists, mock_open, mock_post):
        # Setup mocks
        mock_exists.return_value = True
        
        # Mock file read
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        # When read depends on context, but here we simplify
        mock_file.read.return_value = json.dumps(AUTH_FILE_CONTENT)
        mock_open.return_value = mock_file
        
        # Mock token refresh response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600
        }
        mock_post.return_value.raise_for_status.return_value = None

        # Initialize handler
        handler = GoogleAntigravityChatCompletion()
        
        # Test _get_access_token (should trigger refresh)
        token = handler._get_access_token({})
        
        self.assertEqual(token, "new-access-token")
        mock_post.assert_called_once()
        self.assertIn("refresh_token", mock_post.call_args[1]["data"])

        # Test construction of body
        litellm_params = {"project_id": "test-project"}
        messages = [{"role": "user", "content": "Hello"}]
        data = handler._construct_body("claude-opus-4-5", messages, {}, litellm_params)
        
        self.assertEqual(data["project"], "test-project")
        self.assertEqual(data["model"], "claude-opus-4-5")
        self.assertEqual(data["request"]["contents"][0]["role"], "user")
        self.assertEqual(data["request"]["contents"][0]["parts"][0]["text"], "Hello")
        self.assertEqual(data["userAgent"], "antigravity")

if __name__ == "__main__":
    unittest.main()
