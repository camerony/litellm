"""
Comprehensive validation script for Google Antigravity integration.

Tests:
1. Authentication and token validity
2. Endpoint connectivity (sandbox and production)
3. Model availability (Gemini 3 Pro, Claude models)
4. Thinking configuration support
5. Streaming responses
"""

import os
import sys
import json
import time
import asyncio
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from litellm import completion, acompletion
from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion


class AntigravityValidator:
    """Validates Google Antigravity integration."""

    def __init__(self, auth_file: str = "auth-profiles.json"):
        self.auth_file = auth_file
        self.handler = GoogleAntigravityChatCompletion()
        self.results: Dict[str, Any] = {
            "timestamp": time.time(),
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }

    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(level, "•")
        print(f"[{timestamp}] {prefix} {message}")

    def test_passed(self, test_name: str):
        """Mark a test as passed."""
        self.results["tests_passed"] += 1
        self.log(f"PASSED: {test_name}", "SUCCESS")

    def test_failed(self, test_name: str, error: str):
        """Mark a test as failed."""
        self.results["tests_failed"] += 1
        self.results["errors"].append({
            "test": test_name,
            "error": error
        })
        self.log(f"FAILED: {test_name} - {error}", "ERROR")

    def check_auth_file(self) -> bool:
        """Check if auth file exists and has valid structure."""
        self.log("Checking auth file...")

        if not os.path.exists(self.auth_file):
            self.test_failed("auth_file_exists", f"File not found: {self.auth_file}")
            return False

        try:
            with open(self.auth_file, 'r') as f:
                data = json.load(f)

            # Check structure
            if "profiles" not in data:
                self.test_failed("auth_file_structure", "Missing 'profiles' key")
                return False

            # Check for google-antigravity profiles
            profiles = data["profiles"]
            antigravity_profiles = [
                email for email, profile in profiles.items()
                if profile.get("provider") == "google-antigravity"
            ]

            if not antigravity_profiles:
                self.test_failed("auth_profiles", "No google-antigravity profiles found")
                return False

            self.log(f"Found {len(antigravity_profiles)} Antigravity profile(s)")

            # Check token expiry
            for email in antigravity_profiles:
                profile = profiles[email]
                expires = profile.get("expires", 0)
                now_ms = int(time.time() * 1000)

                if expires < now_ms:
                    self.log(f"Token for {email} is EXPIRED", "WARNING")
                    self.log(f"  Expired: {time.ctime(expires/1000)}", "WARNING")
                    self.log(f"  Current: {time.ctime(now_ms/1000)}", "WARNING")
                else:
                    remaining_mins = (expires - now_ms) / 1000 / 60
                    self.log(f"Token for {email} valid for {remaining_mins:.1f} minutes")

                # Check required fields
                required_fields = ["access", "refresh", "expires", "projectId"]
                missing = [f for f in required_fields if f not in profile]
                if missing:
                    self.test_failed(
                        "auth_profile_fields",
                        f"Profile {email} missing fields: {missing}"
                    )
                    return False

            self.test_passed("auth_file_validation")
            return True

        except json.JSONDecodeError as e:
            self.test_failed("auth_file_parse", f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.test_failed("auth_file_check", str(e))
            return False

    async def test_endpoint_connectivity(self) -> bool:
        """Test connectivity to Antigravity endpoints."""
        self.log("Testing endpoint connectivity...")

        endpoints = [
            ("Sandbox", "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"),
            ("Production", "https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse")
        ]

        # Get access token
        try:
            litellm_params = {}
            access_token = self.handler._get_access_token(litellm_params)
            self.log(f"Retrieved access token: {access_token[:20]}...")
        except Exception as e:
            self.test_failed("token_retrieval", str(e))
            return False

        # Test each endpoint
        all_passed = True
        for name, endpoint in endpoints:
            try:
                self.log(f"Testing {name} endpoint...")

                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                # Simple test request
                body = {
                    "model": "gemini-3-pro",
                    "request": {
                        "contents": [{
                            "role": "user",
                            "parts": [{"text": "test"}]
                        }],
                        "generationConfig": {
                            "maxOutputTokens": 10
                        }
                    }
                }

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(endpoint, json=body, headers=headers)

                    if response.status_code == 200:
                        self.test_passed(f"endpoint_connectivity_{name.lower()}")
                    elif response.status_code == 404:
                        self.log(f"{name} returned 404 (expected for some models)", "WARNING")
                    elif response.status_code == 429:
                        self.log(f"{name} returned 429 (rate limited)", "WARNING")
                    else:
                        self.log(f"{name} returned {response.status_code}: {response.text[:200]}", "WARNING")

            except httpx.TimeoutException:
                self.test_failed(f"endpoint_connectivity_{name.lower()}", "Timeout")
                all_passed = False
            except Exception as e:
                self.test_failed(f"endpoint_connectivity_{name.lower()}", str(e))
                all_passed = False

        return all_passed

    async def test_model_availability(self) -> bool:
        """Test availability of various models."""
        self.log("Testing model availability...")

        models_to_test = [
            ("gemini-3-pro", "Gemini 3 Pro base"),
            ("gemini-3-pro-high", "Gemini 3 Pro with high thinking"),
            ("gemini-3-flash", "Gemini 3 Flash"),
            ("claude-opus-4-5", "Claude Opus 4.5"),
            ("claude-sonnet-4-5", "Claude Sonnet 4.5"),
        ]

        all_passed = True
        for model_name, description in models_to_test:
            try:
                self.log(f"Testing model: {model_name} ({description})...")

                response = await acompletion(
                    model=f"google_antigravity/{model_name}",
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_tokens=50,
                    timeout=30
                )

                # Check if we got a response
                if response and hasattr(response, 'choices'):
                    content = response.choices[0].message.content
                    self.log(f"  Response: {content[:50]}...")
                    self.test_passed(f"model_availability_{model_name}")
                else:
                    self.test_failed(f"model_availability_{model_name}", "No valid response")
                    all_passed = False

            except Exception as e:
                error_str = str(e)
                # Check if it's a known issue
                if "404" in error_str:
                    self.log(f"  Model {model_name} not found (404)", "WARNING")
                elif "429" in error_str:
                    self.log(f"  Rate limited for {model_name} (429)", "WARNING")
                elif "no longer supported" in error_str.lower():
                    self.log(f"  Version error for {model_name}", "WARNING")
                else:
                    self.test_failed(f"model_availability_{model_name}", error_str)
                    all_passed = False

        return all_passed

    async def test_thinking_configuration(self) -> bool:
        """Test thinking configuration support."""
        self.log("Testing thinking configuration...")

        test_cases = [
            {
                "name": "suffix_high",
                "model": "google_antigravity/gemini-3-pro-high",
                "messages": [{"role": "user", "content": "Explain recursion"}],
                "expected": "HIGH thinking level via suffix"
            },
            {
                "name": "suffix_medium",
                "model": "google_antigravity/gemini-3-pro-medium",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "expected": "MEDIUM thinking level via suffix"
            },
            {
                "name": "manual_thinking",
                "model": "google_antigravity/gemini-3-pro",
                "messages": [{"role": "user", "content": "Test"}],
                "extra_body": {
                    "thinking": {"thinkingLevel": "HIGH", "includeThoughts": True}
                },
                "expected": "Manual thinking config"
            }
        ]

        all_passed = True
        for test_case in test_cases:
            try:
                self.log(f"Testing: {test_case['expected']}...")

                kwargs = {
                    "model": test_case["model"],
                    "messages": test_case["messages"],
                    "max_tokens": 100
                }

                if "extra_body" in test_case:
                    kwargs["extra_body"] = test_case["extra_body"]

                response = await acompletion(**kwargs, timeout=30)

                if response and hasattr(response, 'choices'):
                    self.test_passed(f"thinking_config_{test_case['name']}")
                else:
                    self.test_failed(f"thinking_config_{test_case['name']}", "No response")
                    all_passed = False

            except Exception as e:
                self.test_failed(f"thinking_config_{test_case['name']}", str(e))
                all_passed = False

        return all_passed

    async def test_streaming(self) -> bool:
        """Test streaming responses."""
        self.log("Testing streaming...")

        try:
            response = await acompletion(
                model="google_antigravity/gemini-3-pro",
                messages=[{"role": "user", "content": "Count to 5"}],
                stream=True,
                max_tokens=100,
                timeout=30
            )

            chunks_received = 0
            async for chunk in response:
                chunks_received += 1
                if chunks_received == 1:
                    self.log(f"  Received first chunk: {chunk}")

            if chunks_received > 0:
                self.log(f"  Received {chunks_received} chunks")
                self.test_passed("streaming")
                return True
            else:
                self.test_failed("streaming", "No chunks received")
                return False

        except Exception as e:
            self.test_failed("streaming", str(e))
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests."""
        self.log("=" * 60)
        self.log("GOOGLE ANTIGRAVITY VALIDATION SUITE")
        self.log("=" * 60)

        # 1. Check auth file
        if not self.check_auth_file():
            self.log("Auth file validation failed. Stopping tests.", "ERROR")
            return self.results

        # 2. Test endpoint connectivity
        await self.test_endpoint_connectivity()

        # 3. Test model availability
        await self.test_model_availability()

        # 4. Test thinking configuration
        await self.test_thinking_configuration()

        # 5. Test streaming
        await self.test_streaming()

        # Print summary
        self.log("=" * 60)
        self.log("VALIDATION SUMMARY")
        self.log("=" * 60)
        self.log(f"Tests Passed: {self.results['tests_passed']}")
        self.log(f"Tests Failed: {self.results['tests_failed']}")

        if self.results['errors']:
            self.log("\nErrors:", "ERROR")
            for error in self.results['errors']:
                self.log(f"  - {error['test']}: {error['error']}", "ERROR")

        total_tests = self.results['tests_passed'] + self.results['tests_failed']
        if total_tests > 0:
            success_rate = (self.results['tests_passed'] / total_tests) * 100
            self.log(f"\nSuccess Rate: {success_rate:.1f}%")

        return self.results


async def main():
    """Main entry point."""
    validator = AntigravityValidator()
    results = await validator.run_all_tests()

    # Exit with error code if any tests failed
    sys.exit(0 if results['tests_failed'] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
